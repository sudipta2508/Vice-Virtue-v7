"""Default item shapes and evidence helpers for assessment / reassessment graphs."""

from __future__ import annotations


def parse_narrative_to_paragraphs(narrative: str) -> dict:
    paragraphs = [p.strip() for p in (narrative or "").split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in (narrative or "").split("\n") if p.strip()]
    return {f"paragraph_{i + 1}": para for i, para in enumerate(paragraphs)}


def default_evidence_item() -> dict:
    return {
        "virtue_evidences": [],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }


def default_analysis_item() -> dict:
    return {
        "virtue": {
            "frequency": {"supporting": 0, "contradictory": 0, "undefined": 0},
            "consistency": "consistent",
            "type_counts": {"execution": 0, "intention": 0},
            "writing_counts": {"confident": 0, "hedging": 0},
            "level_counts": {
                "level_1": 0,
                "level_2": 0,
                "level_3": 0,
                "level_4": 0,
                "level_5": 0,
            },
            "special_flags": {
                "situationalInconsistency": 0,
                "socialDesirabilityFlags": {"flag": False, "reasoning": ""},
                "negativeBehaviorFlags": {"flag": False, "reasoning": ""},
            },
            "specific_situation_examples": {
                "count": 0,
                "high_intensity_count": 0,
                "medium_intensity_count": 0,
                "low_intensity_count": 0,
            },
        },
        "deficit_vice": {},
        "excess_vice": {},
    }


def default_score_item() -> dict:
    return {
        "virtue_score": 0,
        "deficit_vice_score": 0,
        "excess_vice_score": 0,
        "virtue_reasoning": "No evidence found.",
        "deficit_vice_reasoning": "No evidence found.",
        "excess_vice_reasoning": "No evidence found.",
    }


def default_bh_item() -> dict:
    return {
        "virtue_score": 0,
        "deficit_vice_score": 0,
        "excess_vice_score": 0,
        "reasoning": "No evidence found.",
    }


def default_adjustment_item(scoring_item: dict | None = None) -> dict:
    scoring_item = scoring_item or default_score_item()
    return {
        "virtue_adjustment": 0,
        "deficit_vice_adjustment": 0,
        "excess_vice_adjustment": 0,
        "virtue_score_adjusted": scoring_item.get("virtue_score", 0),
        "deficit_vice_score_adjusted": scoring_item.get("deficit_vice_score", 0),
        "excess_vice_score_adjusted": scoring_item.get("excess_vice_score", 0),
        "adjustment_reasoning": "No additional adjustment.",
    }


def default_coordinator_item(adjustment_item: dict | None = None) -> dict:
    adjustment_item = adjustment_item or default_adjustment_item()
    return {
        "final_virtue_score": adjustment_item.get("virtue_score_adjusted", 0),
        "final_deficit_vice_score": adjustment_item.get("deficit_vice_score_adjusted", 0),
        "final_excess_vice_score": adjustment_item.get("excess_vice_score_adjusted", 0),
        "dominant_class": "uncertain",
        "arbitration_reasoning": "No evidence for any class; scores set to 0.",
    }


def normalize_dimension_result(result, dimension: str) -> dict:
    if isinstance(result, dict) and dimension in result:
        return result[dimension]
    return result if isinstance(result, dict) else {}


def item_has_any_evidence(evidence_item: dict) -> bool:
    if not isinstance(evidence_item, dict):
        return False
    for cls in ("virtue", "deficit_vice", "excess_vice"):
        if evidence_item.get(f"{cls}_evidences"):
            return True
    return False


def dimension_has_any_evidence(evidence_dim: dict, catalog_items: list) -> bool:
    for it in catalog_items:
        if item_has_any_evidence(evidence_dim.get(it["virtue"], {})):
            return True
    return False
