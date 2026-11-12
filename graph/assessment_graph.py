"""LangGraph 5-stage assessment pipeline (replaces pipeline.run_async_analysis)."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from langgraph.graph import END, START, StateGraph

from config import (
    CACHE_POLICY,
    CLASSIFICATION_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    FAST_MODEL,
    MAX_CONCURRENT_DIMENSIONS,
)
from graph.defaults import (
    default_adjustment_item,
    default_analysis_item,
    default_bh_item,
    default_coordinator_item,
    default_evidence_item,
    default_score_item,
    dimension_has_any_evidence,
    item_has_any_evidence,
    normalize_dimension_result,
    parse_narrative_to_paragraphs,
)
from graph.llm import LLMClient, make_llm
from graph.state import AssessmentState
from utils.cache import get_cache, set_cache
from utils.item_postprocess import (
    apply_no_evidence_rule,
    enforce_bh_single_high,
    finalize_coordinator_item,
    zero_adjustment_for_missing_evidence,
)
from graph.evidence_tiers import classify_evidence_tiers
from utils.prompts import (
    create_adjustment_prompt,
    create_behavioural_hierarchy_prompt,
    create_combined_analysis_prompt,
    create_coordinator_prompt,
    create_evidence_collector_prompt,
    create_scoring_prompt,
)


def _noop_progress(stage: str, percent: float, message: str):
    pass


def _add_usage(total: dict, client: LLMClient):
    total["input_tokens"] = total.get("input_tokens", 0) + client.total_input_tokens
    total["output_tokens"] = total.get("output_tokens", 0) + client.total_output_tokens


def _cache_get(narrative: str, agent: str, dimension: str):
    if CACHE_POLICY == "off":
        return None
    return get_cache(narrative, agent, dimension)


def _cache_set(narrative: str, agent: str, dimension: str, data):
    if CACHE_POLICY == "off":
        return
    set_cache(narrative, agent, dimension, data)


async def _stage1_dimension(
    dimension: str,
    items: list,
    paragraphs: dict,
    narrative: str,
    api_key: str,
    model: str,
    usage: dict,
) -> tuple[str, dict, dict]:
    cached_e = _cache_get(narrative, "tri_evidence", dimension)
    cached_bh = _cache_get(narrative, "tri_bh", dimension)
    if cached_e is not None and cached_bh is not None:
        # Ensure tiers exist even on cache hit from older runs
        ev = await classify_evidence_tiers(
            api_key, dimension, items, cached_e, usage, narrative=narrative
        )
        return dimension, ev, cached_bh

    evidence_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    bh_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)

    ev_raw, bh_raw = await asyncio.gather(
        evidence_llm.ainvoke_json(create_evidence_collector_prompt(dimension, items, paragraphs)),
        bh_llm.ainvoke_json(create_behavioural_hierarchy_prompt(dimension, items, paragraphs)),
    )
    _add_usage(usage, evidence_llm)
    _add_usage(usage, bh_llm)

    ev = normalize_dimension_result(ev_raw, dimension)
    bh = normalize_dimension_result(bh_raw, dimension)
    # Stage 1b — evidence strength tiers
    ev = await classify_evidence_tiers(
        api_key, dimension, items, ev, usage, narrative=narrative
    )
    _cache_set(narrative, "tri_evidence", dimension, ev)
    _cache_set(narrative, "tri_bh", dimension, bh)
    return dimension, ev, bh


async def _stages_2_to_5_dimension(
    dimension: str,
    items: list,
    evidence_dim: dict,
    bh_dim: dict,
    narrative: str,
    api_key: str,
    model: str,
    usage: dict,
) -> tuple[str, dict, dict, dict, dict]:
    """Run analysis → scoring → adjustment → coordinator, skipping empty items."""
    # Full-dimension skip when no evidence at all
    if not dimension_has_any_evidence(evidence_dim, items):
        analysis = {it["virtue"]: default_analysis_item() for it in items}
        scoring = {it["virtue"]: default_score_item() for it in items}
        adjustment = {
            it["virtue"]: default_adjustment_item(scoring[it["virtue"]]) for it in items
        }
        coordinator = {
            it["virtue"]: default_coordinator_item(adjustment[it["virtue"]]) for it in items
        }
        return dimension, analysis, scoring, adjustment, coordinator

    # Items with evidence go to LLM; empty items get defaults
    items_with_ev = {
        it["virtue"]: evidence_dim.get(it["virtue"], default_evidence_item())
        for it in items
        if item_has_any_evidence(evidence_dim.get(it["virtue"], {}))
    }
    empty_keys = [it["virtue"] for it in items if it["virtue"] not in items_with_ev]

    analysis: dict = {k: default_analysis_item() for k in empty_keys}
    scoring: dict = {k: default_score_item() for k in empty_keys}
    adjustment: dict = {k: default_adjustment_item(scoring[k]) for k in empty_keys}
    coordinator: dict = {k: default_coordinator_item(adjustment[k]) for k in empty_keys}

    if not items_with_ev:
        return dimension, analysis, scoring, adjustment, coordinator

    # Stage 2 — Combined analysis (fast model)
    cached_analysis = _cache_get(narrative, "tri_analysis", dimension)
    if cached_analysis is not None:
        analysis_dim = cached_analysis
    else:
        analysis_llm = make_llm(api_key, FAST_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
        raw = await analysis_llm.ainvoke_json(
            create_combined_analysis_prompt(dimension, items_with_ev)
        )
        _add_usage(usage, analysis_llm)
        analysis_dim = normalize_dimension_result(raw, dimension)
        _cache_set(narrative, "tri_analysis", dimension, analysis_dim)

    for key in items_with_ev:
        analysis[key] = analysis_dim.get(key) if isinstance(analysis_dim.get(key), dict) else default_analysis_item()

    # Stage 3 — Scoring
    cached_scoring = _cache_get(narrative, "tri_scoring", dimension)
    if cached_scoring is not None:
        scoring_dim = cached_scoring
    else:
        scoring_input = {
            key: {
                "item_meta": next(it for it in items if it["virtue"] == key),
                "evidence": items_with_ev[key],
                "analysis": analysis[key],
            }
            for key in items_with_ev
        }
        scoring_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
        raw = await scoring_llm.ainvoke_json(
            create_scoring_prompt(dimension, scoring_input),
            max_tokens_override=CLASSIFICATION_MAX_TOKENS,
        )
        _add_usage(usage, scoring_llm)
        scoring_dim = normalize_dimension_result(raw, dimension)
        _cache_set(narrative, "tri_scoring", dimension, scoring_dim)

    for key in items_with_ev:
        item = scoring_dim.get(key) if isinstance(scoring_dim.get(key), dict) else default_score_item()
        scoring[key] = apply_no_evidence_rule(item, items_with_ev[key])

    # Stage 4 — Adjustment
    cached_adj = _cache_get(narrative, "tri_adjustment", dimension)
    if cached_adj is not None:
        adj_dim = cached_adj
    else:
        adj_input = {
            key: {
                "item_meta": next(it for it in items if it["virtue"] == key),
                "evidence": items_with_ev[key],
                "analysis": analysis[key],
                "scoring": scoring[key],
            }
            for key in items_with_ev
        }
        adj_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
        raw = await adj_llm.ainvoke_json(
            create_adjustment_prompt(dimension, adj_input),
            max_tokens_override=CLASSIFICATION_MAX_TOKENS,
        )
        _add_usage(usage, adj_llm)
        adj_dim = normalize_dimension_result(raw, dimension)
        _cache_set(narrative, "tri_adjustment", dimension, adj_dim)

    for key in items_with_ev:
        item = adj_dim.get(key) if isinstance(adj_dim.get(key), dict) else default_adjustment_item(scoring[key])
        adjustment[key] = zero_adjustment_for_missing_evidence(item, items_with_ev[key])

    # Stage 5 — Coordinator
    cached_co = _cache_get(narrative, "tri_coordinator", dimension)
    if cached_co is not None:
        co_dim = cached_co
    else:
        co_input = {
            key: {
                "item_meta": next(it for it in items if it["virtue"] == key),
                "evidence": items_with_ev[key],
                "analysis": analysis[key],
                "scoring": scoring[key],
                "adjustment": adjustment[key],
                "behavioral_hierarchy": bh_dim.get(key, default_bh_item()),
            }
            for key in items_with_ev
        }
        co_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
        raw = await co_llm.ainvoke_json(
            create_coordinator_prompt(dimension, co_input),
            max_tokens_override=CLASSIFICATION_MAX_TOKENS,
        )
        _add_usage(usage, co_llm)
        co_dim = normalize_dimension_result(raw, dimension)
        _cache_set(narrative, "tri_coordinator", dimension, co_dim)

    for key in items_with_ev:
        item = co_dim.get(key) if isinstance(co_dim.get(key), dict) else default_coordinator_item(adjustment[key])
        coordinator[key] = finalize_coordinator_item(item, analysis[key], items_with_ev[key])

    # Empty items still get finalize for consistency
    for key in empty_keys:
        coordinator[key] = finalize_coordinator_item(
            coordinator[key], analysis[key], evidence_dim.get(key, default_evidence_item())
        )

    return dimension, analysis, scoring, adjustment, coordinator


async def _node_prepare(state: AssessmentState) -> dict:
    narrative = state.get("narrative") or ""
    catalog = state.get("catalog") or {}
    return {
        "paragraphs": parse_narrative_to_paragraphs(narrative),
        "dimensions": list(catalog.keys()),
        "evidence": {},
        "behavioral_hierarchy": {},
        "analysis": {},
        "scoring": {},
        "adjustment": {},
        "coordinator": {},
        "token_usage": {"input_tokens": 0, "output_tokens": 0},
        "error": None,
    }


async def _node_stage1(state: AssessmentState) -> dict:
    catalog = state["catalog"]
    narrative = state["narrative"]
    paragraphs = state["paragraphs"]
    api_key = state["api_key"]
    model = state.get("model") or DEFAULT_MODEL
    dimensions = state["dimensions"]
    usage = {"input_tokens": 0, "output_tokens": 0}
    sem = asyncio.Semaphore(MAX_CONCURRENT_DIMENSIONS)

    async def _one(dim: str):
        async with sem:
            return await _stage1_dimension(
                dim, catalog[dim], paragraphs, narrative, api_key, model, usage
            )

    results = await asyncio.gather(*[_one(d) for d in dimensions])
    evidence: dict = {}
    bh: dict = {}
    for dimension, ev, bh_raw in results:
        evidence[dimension] = ev if isinstance(ev, dict) else {}
        bh[dimension] = bh_raw if isinstance(bh_raw, dict) else {}
        for item in catalog[dimension]:
            key = item["virtue"]
            evidence[dimension].setdefault(key, default_evidence_item())
            bh_item = bh[dimension].get(key) if isinstance(bh[dimension].get(key), dict) else default_bh_item()
            bh[dimension][key] = enforce_bh_single_high(bh_item, evidence[dimension][key])

    prev = state.get("token_usage") or {}
    return {
        "evidence": evidence,
        "behavioral_hierarchy": bh,
        "token_usage": {
            "input_tokens": prev.get("input_tokens", 0) + usage["input_tokens"],
            "output_tokens": prev.get("output_tokens", 0) + usage["output_tokens"],
        },
    }


async def _node_stages_2_to_5(state: AssessmentState) -> dict:
    catalog = state["catalog"]
    narrative = state["narrative"]
    api_key = state["api_key"]
    model = state.get("model") or DEFAULT_MODEL
    dimensions = state["dimensions"]
    evidence = state["evidence"]
    bh = state["behavioral_hierarchy"]
    usage = {"input_tokens": 0, "output_tokens": 0}
    sem = asyncio.Semaphore(MAX_CONCURRENT_DIMENSIONS)

    async def _one(dim: str):
        async with sem:
            return await _stages_2_to_5_dimension(
                dim,
                catalog[dim],
                evidence.get(dim, {}),
                bh.get(dim, {}),
                narrative,
                api_key,
                model,
                usage,
            )

    results = await asyncio.gather(*[_one(d) for d in dimensions])
    analysis: dict = {}
    scoring: dict = {}
    adjustment: dict = {}
    coordinator: dict = {}
    for dimension, a, s, adj, co in results:
        analysis[dimension] = a
        scoring[dimension] = s
        adjustment[dimension] = adj
        coordinator[dimension] = co

    prev = state.get("token_usage") or {}
    return {
        "analysis": analysis,
        "scoring": scoring,
        "adjustment": adjustment,
        "coordinator": coordinator,
        "token_usage": {
            "input_tokens": prev.get("input_tokens", 0) + usage["input_tokens"],
            "output_tokens": prev.get("output_tokens", 0) + usage["output_tokens"],
        },
    }


def build_assessment_graph():
    g = StateGraph(AssessmentState)
    g.add_node("prepare", _node_prepare)
    g.add_node("stage1_evidence_bh", _node_stage1)
    g.add_node("stages_2_to_5", _node_stages_2_to_5)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "stage1_evidence_bh")
    g.add_edge("stage1_evidence_bh", "stages_2_to_5")
    g.add_edge("stages_2_to_5", END)
    return g.compile()


_ASSESSMENT_GRAPH = None


def get_assessment_graph():
    global _ASSESSMENT_GRAPH
    if _ASSESSMENT_GRAPH is None:
        _ASSESSMENT_GRAPH = build_assessment_graph()
    return _ASSESSMENT_GRAPH


async def run_async_analysis(
    api_key: str,
    model: str,
    selected_catalog: dict,
    narrative: str,
    on_progress: Optional[Callable[[str, float, str], None]] = None,
) -> dict:
    """Public entry point — same return shape as legacy pipeline.run_async_analysis."""
    progress = on_progress or _noop_progress
    progress("stage1", 0.0, "Stage 1: Collect evidence + behavioral hierarchy")

    graph = get_assessment_graph()
    # Run stage1 with progress updates around graph invoke by splitting:
    # We invoke the full graph; emit progress before/after via wrapping nodes is hard,
    # so emit coarse progress markers around ainvoke.
    initial: AssessmentState = {
        "api_key": api_key,
        "model": model or DEFAULT_MODEL,
        "catalog": selected_catalog,
        "narrative": narrative,
    }

    # Manual two-step so progress reporting matches the UI contract
    state = await _node_prepare(initial)
    merged = {**initial, **state}
    progress("stage1", 0.05, "Stage 1: Collect evidence + behavioral hierarchy")
    progress("stage1b", 0.1, "Stage 1b: classifying evidence strength")
    stage1 = await _node_stage1(merged)
    merged.update(stage1)
    progress("stage1", 0.25, "Stage 1 complete")
    progress("stage2", 0.25, "Stages 2–5: Analysis, scoring, adjustment, coordinator")
    rest = await _node_stages_2_to_5(merged)
    merged.update(rest)
    progress("stage5", 1.0, "Analysis complete")

    return {
        "evidence": merged.get("evidence", {}),
        "behavioral_hierarchy": merged.get("behavioral_hierarchy", {}),
        "analysis": merged.get("analysis", {}),
        "scoring": merged.get("scoring", {}),
        "adjustment": merged.get("adjustment", {}),
        "coordinator": merged.get("coordinator", {}),
        "token_usage": merged.get("token_usage")
        or {"input_tokens": 0, "output_tokens": 0},
    }
