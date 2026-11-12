"""Transform pipeline output into React-friendly shapes."""

from __future__ import annotations

import re
from collections import defaultdict

from config import EVIDENCE_TIER_FALLBACK, EVIDENCE_TIER_WEIGHTS
from dimension_means import class_has_evidence, compute_dimension_means
from graph.evidence_tiers import normalize_tier, tier_weight, weighted_strength
from .dimension_metadata import DIMENSION_META, JUDGMENT_NAME, WHEEL_ORDER

# Internal class key -> short display label used in also_used hashtags
_CLASS_DISPLAY = {
    "virtue": "virtue",
    "deficit_vice": "deficit",
    "excess_vice": "excess",
}
_EVIDENCE_CLASS_KEYS = ("virtue", "deficit_vice", "excess_vice")


def _normalize_evidence_text(text) -> str:
    """Normalize snippet text for cross-reference matching."""
    if not isinstance(text, str):
        return ""
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed.casefold()


def _build_evidence_crossref_index(output: dict, catalog: dict) -> dict[str, list[dict]]:
    """Map normalized evidence text -> list of {dimension, item, cls} locations."""
    index: dict[str, list[dict]] = defaultdict(list)
    evidence_root = (output or {}).get("evidence") or {}

    for dimension, items in (catalog or {}).items():
        dim_ev = evidence_root.get(dimension) or {}
        for item in items:
            item_key = item["virtue"]
            item_ev = dim_ev.get(item_key) or {}
            if not isinstance(item_ev, dict):
                continue
            for cls in _EVIDENCE_CLASS_KEYS:
                snippets = item_ev.get(f"{cls}_evidences") or []
                if not isinstance(snippets, list):
                    continue
                display_cls = _CLASS_DISPLAY[cls]
                for ev in snippets:
                    if not isinstance(ev, dict):
                        continue
                    key = _normalize_evidence_text(ev.get("text", ""))
                    if not key:
                        continue
                    loc = {"dimension": dimension, "item": item_key, "cls": display_cls}
                    # Deduplicate identical locations for the same text
                    if loc not in index[key]:
                        index[key].append(loc)

    for key in index:
        index[key].sort(key=lambda loc: (loc["dimension"], loc["item"], loc["cls"]))
    return dict(index)


def _also_used_for(
    index: dict[str, list[dict]],
    text: str,
    dimension: str,
    item: str,
    cls: str,
) -> list[dict]:
    """Other placements of the same text, excluding the current location."""
    key = _normalize_evidence_text(text)
    if not key:
        return []
    display_cls = _CLASS_DISPLAY.get(cls, cls)
    current = {"dimension": dimension, "item": item, "cls": display_cls}
    return [loc for loc in index.get(key, []) if loc != current]


def _score_or_null(value):
    """Pass through None for missing evidence; otherwise round to 2 decimals."""
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _item_class_score(co: dict, evidence: dict, cls: str, score_key: str):
    """Return coordinator score, or None when that class has no evidence snippets."""
    if not class_has_evidence(evidence, cls):
        return None
    try:
        return int(co.get(score_key, 0))
    except (TypeError, ValueError):
        return 0


def build_dimension_chart_data(output: dict, catalog: dict) -> dict:
    """Build wheel chart data: dimensions list + judgment center."""
    means = compute_dimension_means(output, catalog)
    dimensions = []

    for name in WHEEL_ORDER:
        if name not in catalog:
            continue
        meta = DIMENSION_META.get(name, {})
        m = means.get(name, {})
        items = catalog.get(name, [])
        traits = [it["virtue"] for it in items]

        dimensions.append(
            {
                "name": name,
                "color": meta.get("color", "#8A8680"),
                "angle": meta.get("angle", 0),
                "traits": traits,
                "description": meta.get("description", ""),
                "deficit": {
                    "name": meta.get("deficit_name", "Deficit"),
                    "score": _score_or_null(m.get("deficit_vice")),
                    "desc": meta.get("deficit_desc", ""),
                },
                "virtue": {
                    "score": _score_or_null(m.get("virtue")),
                    "desc": "",
                },
                "excess": {
                    "name": meta.get("excess_name", "Excess"),
                    "score": _score_or_null(m.get("excess_vice")),
                    "desc": meta.get("excess_desc", ""),
                },
            }
        )

    judgment_meta = DIMENSION_META.get(JUDGMENT_NAME, {})
    jm = means.get(JUDGMENT_NAME, {})
    j_items = catalog.get(JUDGMENT_NAME, [])
    judgment = {
        "name": JUDGMENT_NAME,
        "color": judgment_meta.get("color", "#A09C94"),
        "angle": 0,
        "traits": [it["virtue"] for it in j_items],
        "description": judgment_meta.get("description", ""),
        "deficit": {
            "name": judgment_meta.get("deficit_name", "Indecisiveness"),
            "score": _score_or_null(jm.get("deficit_vice")),
            "desc": judgment_meta.get("deficit_desc", ""),
        },
        "virtue": {
            "score": _score_or_null(jm.get("virtue")),
            "desc": "",
        },
        "excess": {
            "name": judgment_meta.get("excess_name", "Stubbornness"),
            "score": _score_or_null(jm.get("excess_vice")),
            "desc": judgment_meta.get("excess_desc", ""),
        },
    }

    return {"dimensions": dimensions, "judgment": judgment}


def _extract_flags(analysis_cls: dict) -> dict:
    if not isinstance(analysis_cls, dict):
        return {}
    sf = analysis_cls.get("special_flags", {}) or {}
    sd = sf.get("socialDesirabilityFlags", {}) or {}
    nb = sf.get("negativeBehaviorFlags", {}) or {}
    return {
        "situationalInconsistency": sf.get("situationalInconsistency", 0),
        "socialDesirability": bool(sd.get("flag", False)),
        "socialDesirabilityReasoning": sd.get("reasoning", ""),
        "negativeBehavior": bool(nb.get("flag", False)),
        "negativeBehaviorReasoning": nb.get("reasoning", ""),
        "frequency": analysis_cls.get("frequency", {}),
        "consistency": analysis_cls.get("consistency", ""),
        "type_counts": analysis_cls.get("type_counts", {}),
        "writing_counts": analysis_cls.get("writing_counts", {}),
    }


def build_dimension_items(output: dict, catalog: dict, dimension: str) -> list[dict]:
    """Item-level detail for Explore mode."""
    crossref = _build_evidence_crossref_index(output, catalog)
    items_out = []
    for item in catalog.get(dimension, []):
        key = item["virtue"]
        evidence = output.get("evidence", {}).get(dimension, {}).get(key, {})
        analysis = output.get("analysis", {}).get(dimension, {}).get(key, {})
        scoring = output.get("scoring", {}).get(dimension, {}).get(key, {})
        adjustment = output.get("adjustment", {}).get(dimension, {}).get(key, {})
        co = output.get("coordinator", {}).get(dimension, {}).get(key, {})
        bh = output.get("behavioral_hierarchy", {}).get(dimension, {}).get(key, {})

        def _ev_list(cls: str, item_key: str = key) -> list:
            raw = evidence.get(f"{cls}_evidences", []) or []
            out = []
            for ev in raw:
                if not isinstance(ev, dict):
                    continue
                tier = normalize_tier(ev.get("strength_tier") or EVIDENCE_TIER_FALLBACK)
                if tier not in EVIDENCE_TIER_WEIGHTS:
                    tier = EVIDENCE_TIER_FALLBACK
                weight = ev.get("weight")
                if weight is None:
                    weight = tier_weight(tier)
                text = ev.get("text", "")
                out.append(
                    {
                        "id": ev.get("evidence_id", ""),
                        "text": text,
                        "source_position": ev.get("source_position", ""),
                        "strength_tier": tier,
                        "weight": weight,
                        "tier_reasoning": ev.get("tier_reasoning", "") or "",
                        "also_used": _also_used_for(crossref, text, dimension, item_key, cls),
                    }
                )
            return out

        items_out.append(
            {
                "virtue": key,
                "scores": {
                    "virtue": _item_class_score(co, evidence, "virtue", "final_virtue_score"),
                    "deficit_vice": _item_class_score(
                        co, evidence, "deficit_vice", "final_deficit_vice_score"
                    ),
                    "excess_vice": _item_class_score(
                        co, evidence, "excess_vice", "final_excess_vice_score"
                    ),
                    "dominant_class": co.get("dominant_class", "uncertain"),
                    "raw_scoring": {
                        "virtue": _item_class_score(scoring, evidence, "virtue", "virtue_score"),
                        "deficit_vice": _item_class_score(
                            scoring, evidence, "deficit_vice", "deficit_vice_score"
                        ),
                        "excess_vice": _item_class_score(
                            scoring, evidence, "excess_vice", "excess_vice_score"
                        ),
                    },
                    "adjusted": {
                        "virtue": _item_class_score(
                            adjustment, evidence, "virtue", "virtue_score_adjusted"
                        ),
                        "deficit_vice": _item_class_score(
                            adjustment, evidence, "deficit_vice", "deficit_vice_score_adjusted"
                        ),
                        "excess_vice": _item_class_score(
                            adjustment, evidence, "excess_vice", "excess_vice_score_adjusted"
                        ),
                    },
                    "behavioral_hierarchy": {
                        "virtue": _item_class_score(bh, evidence, "virtue", "virtue_score"),
                        "deficit_vice": _item_class_score(
                            bh, evidence, "deficit_vice", "deficit_vice_score"
                        ),
                        "excess_vice": _item_class_score(
                            bh, evidence, "excess_vice", "excess_vice_score"
                        ),
                    },
                },
                "reasoning": {
                    "virtue": scoring.get("virtue_reasoning", ""),
                    "deficit_vice": scoring.get("deficit_vice_reasoning", ""),
                    "excess_vice": scoring.get("excess_vice_reasoning", ""),
                    "adjustment": adjustment.get("adjustment_reasoning", ""),
                    "coordinator": co.get("arbitration_reasoning", ""),
                    "arbitration": co.get("arbitration_reasoning", ""),
                    "behavioral_hierarchy": bh.get("reasoning", ""),
                },
                "arbitration_reasoning": co.get("arbitration_reasoning", ""),
                "flags": {
                    "virtue": _extract_flags(analysis.get("virtue", {})),
                    "deficit_vice": _extract_flags(analysis.get("deficit_vice", {})),
                    "excess_vice": _extract_flags(analysis.get("excess_vice", {})),
                },
                "evidence": {
                    "virtue": _ev_list("virtue"),
                    "deficit_vice": _ev_list("deficit_vice"),
                    "excess_vice": _ev_list("excess_vice"),
                },
                "evidence_strength": {
                    "virtue": weighted_strength(evidence, "virtue"),
                    "deficit_vice": weighted_strength(evidence, "deficit_vice"),
                    "excess_vice": weighted_strength(evidence, "excess_vice"),
                },
                "catalog": {
                    "item_description": item.get("item_description", ""),
                    "deficit_vice": item.get("deficit_vice", ""),
                    "deficit_vice_description": item.get("deficit_vice_description", ""),
                    "excess_vice": item.get("excess_vice", ""),
                    "excess_vice_definition": item.get("excess_vice_definition", ""),
                },
            }
        )
    return items_out


def build_catalog_response(catalog: dict) -> dict:
    """Catalog metadata for frontend."""
    dimensions = []
    for name in list(WHEEL_ORDER) + [JUDGMENT_NAME]:
        if name not in catalog:
            continue
        meta = DIMENSION_META.get(name, {})
        items = catalog[name]
        dimensions.append(
            {
                "name": name,
                "color": meta.get("color", "#8A8680"),
                "angle": meta.get("angle", 0),
                "is_center": meta.get("is_center", False),
                "description": meta.get("description", ""),
                "deficit_name": meta.get("deficit_name", ""),
                "excess_name": meta.get("excess_name", ""),
                "traits": [it["virtue"] for it in items],
                "items": [
                    {
                        "virtue": it["virtue"],
                        "item_description": it.get("item_description", ""),
                        "deficit_vice": it.get("deficit_vice", ""),
                        "excess_vice": it.get("excess_vice", ""),
                    }
                    for it in items
                ],
            }
        )
    return {"dimensions": dimensions}
