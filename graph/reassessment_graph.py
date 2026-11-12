"""LangGraph reassessment subgraph — stages 2–5 for items with new follow-up evidence."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from langgraph.graph import END, START, StateGraph

from config import (
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
    default_score_item,
    item_has_any_evidence,
    normalize_dimension_result,
)
from graph.llm import make_llm
from graph.state import ReassessmentState
from utils.item_postprocess import (
    apply_no_evidence_rule,
    enforce_bh_single_high,
    finalize_coordinator_item,
    zero_adjustment_for_missing_evidence,
)
from utils.prompts import (
    create_adjustment_prompt,
    create_behavioural_hierarchy_evidence_only_prompt,
    create_combined_analysis_prompt,
    create_coordinator_prompt,
    create_scoring_prompt,
)


def _add_usage(total: dict, client):
    total["input_tokens"] = total.get("input_tokens", 0) + client.total_input_tokens
    total["output_tokens"] = total.get("output_tokens", 0) + client.total_output_tokens


async def reassess_single_item(
    api_key: str,
    model: str,
    dimension: str,
    item_key: str,
    item_meta: dict,
    working_out: dict,
    merged_evidence: dict,
    status_callback: Optional[Callable[[str], None]] = None,
) -> dict[str, int]:
    """Re-run stages 2–5 for one item; mutates working_out in place."""

    def _status(msg: str):
        if status_callback:
            status_callback(msg)

    usage = {"input_tokens": 0, "output_tokens": 0}
    working_out["evidence"][dimension][item_key] = merged_evidence

    # Skip LLM entirely when somehow still empty
    if not item_has_any_evidence(merged_evidence):
        bh_item = default_bh_item()
        analysis_item = default_analysis_item()
        scoring_item = default_score_item()
        adjustment_item = default_adjustment_item(scoring_item)
        co_item = finalize_coordinator_item(
            default_coordinator_item(adjustment_item), analysis_item, merged_evidence
        )
        working_out["behavioral_hierarchy"][dimension][item_key] = bh_item
        working_out["analysis"][dimension][item_key] = analysis_item
        working_out["scoring"][dimension][item_key] = scoring_item
        working_out["adjustment"][dimension][item_key] = adjustment_item
        working_out["coordinator"][dimension][item_key] = co_item
        return usage

    model = model or DEFAULT_MODEL

    _status(f"Re-scoring behavioral hierarchy ({item_key})…")
    bh_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    bh_raw = await bh_llm.ainvoke_json(
        create_behavioural_hierarchy_evidence_only_prompt(dimension, item_meta, merged_evidence),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    _add_usage(usage, bh_llm)
    bh_dim = normalize_dimension_result(bh_raw, dimension)
    bh_item = bh_dim.get(item_key) if isinstance(bh_dim, dict) else None
    if not isinstance(bh_item, dict):
        bh_item = default_bh_item()
        bh_item["reasoning"] = "Evidence-only BH parse fallback."
    bh_item = enforce_bh_single_high(bh_item, merged_evidence)
    working_out["behavioral_hierarchy"][dimension][item_key] = bh_item

    _status(f"Re-analyzing evidence ({item_key})…")
    analysis_llm = make_llm(api_key, FAST_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    analysis_raw = await analysis_llm.ainvoke_json(
        create_combined_analysis_prompt(dimension, {item_key: merged_evidence})
    )
    _add_usage(usage, analysis_llm)
    analysis_dim = normalize_dimension_result(analysis_raw, dimension)
    analysis_item = analysis_dim.get(item_key) if isinstance(analysis_dim, dict) else None
    if not isinstance(analysis_item, dict):
        analysis_item = default_analysis_item()
    working_out["analysis"][dimension][item_key] = analysis_item

    _status(f"Re-scoring tri-class ({item_key})…")
    scoring_input = {
        item_key: {
            "item_meta": item_meta,
            "evidence": merged_evidence,
            "analysis": analysis_item,
        }
    }
    scoring_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    scoring_raw = await scoring_llm.ainvoke_json(
        create_scoring_prompt(dimension, scoring_input),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    _add_usage(usage, scoring_llm)
    scoring_dim = normalize_dimension_result(scoring_raw, dimension)
    scoring_item = scoring_dim.get(item_key) if isinstance(scoring_dim, dict) else None
    if not isinstance(scoring_item, dict):
        scoring_item = default_score_item()
    scoring_item = apply_no_evidence_rule(scoring_item, merged_evidence)
    working_out["scoring"][dimension][item_key] = scoring_item

    _status(f"Re-adjusting ({item_key})…")
    adjustment_input = {
        item_key: {
            "item_meta": item_meta,
            "evidence": merged_evidence,
            "analysis": analysis_item,
            "scoring": scoring_item,
        }
    }
    adj_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    adjustment_raw = await adj_llm.ainvoke_json(
        create_adjustment_prompt(dimension, adjustment_input),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    _add_usage(usage, adj_llm)
    adjustment_dim = normalize_dimension_result(adjustment_raw, dimension)
    adjustment_item = adjustment_dim.get(item_key) if isinstance(adjustment_dim, dict) else None
    if not isinstance(adjustment_item, dict):
        adjustment_item = default_adjustment_item(scoring_item)
        adjustment_item["adjustment_reasoning"] = "Parse fallback."
    adjustment_item = zero_adjustment_for_missing_evidence(adjustment_item, merged_evidence)
    working_out["adjustment"][dimension][item_key] = adjustment_item

    _status(f"Coordinator arbitration ({item_key})…")
    coordinator_input = {
        item_key: {
            "item_meta": item_meta,
            "evidence": merged_evidence,
            "analysis": analysis_item,
            "scoring": scoring_item,
            "adjustment": adjustment_item,
            "behavioral_hierarchy": bh_item,
        }
    }
    co_llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    coordinator_raw = await co_llm.ainvoke_json(
        create_coordinator_prompt(dimension, coordinator_input),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    _add_usage(usage, co_llm)
    coordinator_dim = normalize_dimension_result(coordinator_raw, dimension)
    co_item = coordinator_dim.get(item_key) if isinstance(coordinator_dim, dict) else None
    if not isinstance(co_item, dict):
        co_item = default_coordinator_item(adjustment_item)
        co_item["arbitration_reasoning"] = "Parse fallback."
    co_item = finalize_coordinator_item(co_item, analysis_item, merged_evidence)
    working_out["coordinator"][dimension][item_key] = co_item
    return usage


async def reassess_items_parallel(
    api_key: str,
    model: str,
    catalog: dict,
    working_out: dict,
    targets: dict[str, list[str]],
    status_callback: Optional[Callable[[str], None]] = None,
) -> dict[str, int]:
    if not targets:
        return {"input_tokens": 0, "output_tokens": 0}

    sem = asyncio.Semaphore(MAX_CONCURRENT_DIMENSIONS)

    async def _one(dim: str, item_key: str):
        async with sem:
            item_meta = next(
                (it for it in catalog[dim] if it["virtue"] == item_key),
                {"virtue": item_key},
            )
            merged = working_out["evidence"][dim][item_key]
            return await reassess_single_item(
                api_key,
                model,
                dim,
                item_key,
                item_meta,
                working_out,
                merged,
                status_callback=status_callback,
            )

    tasks = [_one(dim, item_key) for dim, keys in targets.items() for item_key in keys]
    results = await asyncio.gather(*tasks)
    return {
        "input_tokens": sum(r["input_tokens"] for r in results),
        "output_tokens": sum(r["output_tokens"] for r in results),
    }


async def _node_reassess(state: ReassessmentState) -> dict:
    usage = await reassess_items_parallel(
        state["api_key"],
        state.get("model") or DEFAULT_MODEL,
        state["catalog"],
        state["working_out"],
        {d: keys for d, keys in (state.get("targets") or {}).items() if keys},
    )
    return {"token_usage": usage, "working_out": state["working_out"]}


def build_reassessment_graph():
    g = StateGraph(ReassessmentState)
    g.add_node("reassess", _node_reassess)
    g.add_edge(START, "reassess")
    g.add_edge("reassess", END)
    return g.compile()


_REASSESSMENT_GRAPH = None


def get_reassessment_graph():
    global _REASSESSMENT_GRAPH
    if _REASSESSMENT_GRAPH is None:
        _REASSESSMENT_GRAPH = build_reassessment_graph()
    return _REASSESSMENT_GRAPH
