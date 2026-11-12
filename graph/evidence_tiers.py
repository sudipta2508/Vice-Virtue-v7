"""Stage 1b: classify evidence snippets into Explicit / Strong-implicit / Weak tiers."""

from __future__ import annotations

from typing import Any

from config import (
    CACHE_POLICY,
    CLASSIFICATION_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    EVIDENCE_TIER_FALLBACK,
    EVIDENCE_TIER_MODEL,
    EVIDENCE_TIER_WEIGHTS,
)
from graph.defaults import default_evidence_item, item_has_any_evidence, normalize_dimension_result
from graph.llm import make_llm
from utils.cache import get_cache, set_cache
from utils.prompts import create_evidence_tier_prompt

EVIDENCE_CLASSES = ("virtue", "deficit_vice", "excess_vice")
VALID_TIERS = frozenset(EVIDENCE_TIER_WEIGHTS.keys())


def tier_weight(tier: str | None) -> float:
    if tier in EVIDENCE_TIER_WEIGHTS:
        return float(EVIDENCE_TIER_WEIGHTS[tier])
    return float(EVIDENCE_TIER_WEIGHTS[EVIDENCE_TIER_FALLBACK])


def normalize_tier(raw: Any) -> str:
    if not isinstance(raw, str):
        return EVIDENCE_TIER_FALLBACK
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "explicit": "explicit",
        "strong_implicit": "strong_implicit",
        "strongimplicit": "strong_implicit",
        "implicit": "strong_implicit",
        "weak": "weak",
        "weak_implicit": "weak",
    }
    return aliases.get(key, EVIDENCE_TIER_FALLBACK if key not in VALID_TIERS else key)


def _snippet_id(ev: dict) -> Any:
    return ev.get("evidence_id", ev.get("id"))


def _tier_lookup(tiers_payload: Any) -> dict[tuple[Any, str], dict]:
    """Map (evidence_id, cls) -> {strength_tier, tier_reasoning} from LLM output."""
    lookup: dict[tuple[Any, str], dict] = {}
    if not isinstance(tiers_payload, dict):
        return lookup

    # Shape A: {item: {tiers: [...]}} or {item: [...]}
    # Shape B: flat list under dimension already normalized away
    for _item_key, payload in tiers_payload.items():
        entries = []
        if isinstance(payload, dict):
            entries = payload.get("tiers") or payload.get("classifications") or []
            # Also allow per-class lists
            if not entries:
                for cls in EVIDENCE_CLASSES:
                    for entry in payload.get(cls, []) or []:
                        if isinstance(entry, dict):
                            e = dict(entry)
                            e.setdefault("cls", cls)
                            entries.append(e)
        elif isinstance(payload, list):
            entries = payload
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("evidence_id", entry.get("id"))
            cls = (entry.get("cls") or entry.get("class") or "").strip()
            if eid is None or cls not in EVIDENCE_CLASSES:
                continue
            lookup[(eid, cls)] = {
                "strength_tier": normalize_tier(entry.get("strength_tier") or entry.get("tier")),
                "tier_reasoning": (entry.get("tier_reasoning") or entry.get("reasoning") or "").strip(),
            }
    return lookup


def merge_tiers(evidence_dim: dict, tiers: dict | None) -> dict:
    """Write strength_tier, weight, tier_reasoning onto each snippet. Mutates and returns evidence_dim."""
    lookup = _tier_lookup(tiers or {})
    for _item_key, item in (evidence_dim or {}).items():
        if not isinstance(item, dict):
            continue
        for cls in EVIDENCE_CLASSES:
            key = f"{cls}_evidences"
            snippets = item.get(key) or []
            if not isinstance(snippets, list):
                continue
            for ev in snippets:
                if not isinstance(ev, dict):
                    continue
                eid = _snippet_id(ev)
                hit = lookup.get((eid, cls)) if eid is not None else None
                if hit is None:
                    # Try string/int id variants
                    for alt in (str(eid) if eid is not None else None,):
                        if alt is not None and (alt, cls) in lookup:
                            hit = lookup[(alt, cls)]
                            break
                        try:
                            if eid is not None and (int(eid), cls) in lookup:
                                hit = lookup[(int(eid), cls)]
                                break
                        except (TypeError, ValueError):
                            pass
                tier = hit["strength_tier"] if hit else EVIDENCE_TIER_FALLBACK
                if tier not in VALID_TIERS:
                    tier = EVIDENCE_TIER_FALLBACK
                ev["strength_tier"] = tier
                ev["weight"] = tier_weight(tier)
                if hit and hit.get("tier_reasoning"):
                    ev["tier_reasoning"] = hit["tier_reasoning"]
                else:
                    ev.setdefault("tier_reasoning", "Fallback tier (classifier miss).")
    return evidence_dim


def weighted_strength(evidence_item: dict | None, cls: str) -> float:
    """Sum of snippet weights for a class. Missing weight uses fallback tier weight."""
    if not isinstance(evidence_item, dict):
        return 0.0
    snippets = evidence_item.get(f"{cls}_evidences", []) or []
    total = 0.0
    fallback_w = tier_weight(EVIDENCE_TIER_FALLBACK)
    for ev in snippets:
        if not isinstance(ev, dict):
            continue
        w = ev.get("weight")
        if w is None:
            w = tier_weight(ev.get("strength_tier")) if ev.get("strength_tier") else fallback_w
        try:
            total += float(w)
        except (TypeError, ValueError):
            total += fallback_w
    return round(total, 4)


def apply_fallback_tiers(evidence_dim: dict) -> dict:
    """Stamp fallback tier/weight on every snippet (no LLM)."""
    return merge_tiers(evidence_dim, {})


def _dimension_has_snippets(evidence_dim: dict, items: list) -> bool:
    for it in items:
        key = it["virtue"]
        if item_has_any_evidence(evidence_dim.get(key, default_evidence_item())):
            return True
    return False


async def classify_evidence_tiers(
    api_key: str,
    dimension: str,
    items: list,
    evidence_dim: dict,
    usage: dict | None = None,
    *,
    narrative: str | None = None,
    model: str | None = None,
) -> dict:
    """Classify tiers for a dimension's evidence; merge onto snippets; return enriched evidence_dim.

    Cached under agent name ``tri_evidence_tiers`` when narrative is provided and CACHE_POLICY allows.
    Skips the LLM when the dimension has no evidence (applies fallback stamps only).
    """
    if not evidence_dim:
        return evidence_dim or {}

    if not _dimension_has_snippets(evidence_dim, items):
        return apply_fallback_tiers(evidence_dim)

    cached = None
    if narrative and CACHE_POLICY != "off":
        cached = get_cache(narrative, "tri_evidence_tiers", dimension)
        if cached is not None and isinstance(cached, dict) and "evidence" in cached:
            return cached["evidence"]

    # Build compact evidence for the prompt (only items with snippets)
    compact = {}
    for it in items:
        key = it["virtue"]
        item_ev = evidence_dim.get(key)
        if item_has_any_evidence(item_ev or {}):
            compact[key] = item_ev

    llm = make_llm(
        api_key,
        model or EVIDENCE_TIER_MODEL,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TEMPERATURE,
    )
    raw = await llm.ainvoke_json(
        create_evidence_tier_prompt(dimension, items, compact),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    if usage is not None:
        usage["input_tokens"] = usage.get("input_tokens", 0) + llm.total_input_tokens
        usage["output_tokens"] = usage.get("output_tokens", 0) + llm.total_output_tokens

    tiers_dim = normalize_dimension_result(raw, dimension)
    enriched = merge_tiers(evidence_dim, tiers_dim)

    if narrative and CACHE_POLICY != "off":
        set_cache(narrative, "tri_evidence_tiers", dimension, {"evidence": enriched})

    return enriched
