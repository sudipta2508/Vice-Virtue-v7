"""Shared post-processing for tri-class scores (initial pipeline and reassessment)."""

from config import (
    HIGH_SCORE_MIN_STRENGTH,
    HIGH_THRESHOLD,
    LOW_MAX,
    UNCERTAINTY_SCORE,
    WEAK_ONLY_MAX_SCORE,
)
from graph.evidence_tiers import weighted_strength


def count_evidence(evidence_item, cls):
    return len(evidence_item.get(f"{cls}_evidences", []) or [])


def apply_strength_cap(scores, evidence_item, keys):
    """Cap class scores when weighted evidence strength is below HIGH_SCORE_MIN_STRENGTH.

    ``keys`` maps class name -> score field name, e.g.
    ``{"virtue": "virtue_score", ...}`` or final_/adjusted_ key variants.
    """
    for cls, key in keys.items():
        strength = weighted_strength(evidence_item, cls)
        if strength < HIGH_SCORE_MIN_STRENGTH:
            try:
                current = int(scores.get(key, 0) or 0)
            except (TypeError, ValueError):
                current = 0
            if current > WEAK_ONLY_MAX_SCORE:
                scores[key] = WEAK_ONLY_MAX_SCORE
    return scores


def apply_no_evidence_rule(score_item, evidence_item):
    for cls, key in [
        ("virtue", "virtue_score"),
        ("deficit_vice", "deficit_vice_score"),
        ("excess_vice", "excess_vice_score"),
    ]:
        if count_evidence(evidence_item, cls) == 0:
            score_item[key] = 0
    return apply_strength_cap(
        score_item,
        evidence_item,
        {
            "virtue": "virtue_score",
            "deficit_vice": "deficit_vice_score",
            "excess_vice": "excess_vice_score",
        },
    )


def zero_bh_for_missing_evidence(bh_item, evidence_item):
    """Force BH class scores to 0 when that class has no evidence snippets."""
    if count_evidence(evidence_item, "virtue") == 0:
        bh_item["virtue_score"] = 0
    if count_evidence(evidence_item, "deficit_vice") == 0:
        bh_item["deficit_vice_score"] = 0
    if count_evidence(evidence_item, "excess_vice") == 0:
        bh_item["excess_vice_score"] = 0
    return bh_item


def enforce_bh_single_high(bh_item, evidence_item):
    bh_item = zero_bh_for_missing_evidence(bh_item, evidence_item)
    v = int(bh_item.get("virtue_score", 0))
    d = int(bh_item.get("deficit_vice_score", 0))
    e = int(bh_item.get("excess_vice_score", 0))
    # All-empty evidence: stay at zeros (never leave uncertainty 3/3/3)
    if (
        count_evidence(evidence_item, "virtue") == 0
        and count_evidence(evidence_item, "deficit_vice") == 0
        and count_evidence(evidence_item, "excess_vice") == 0
    ):
        return bh_item
    if v == UNCERTAINTY_SCORE and d == UNCERTAINTY_SCORE and e == UNCERTAINTY_SCORE:
        return bh_item
    highs = []
    if v >= HIGH_THRESHOLD:
        highs.append(("v", v))
    if d >= HIGH_THRESHOLD:
        highs.append(("d", d))
    if e >= HIGH_THRESHOLD:
        highs.append(("e", e))
    if len(highs) <= 1:
        return bh_item
    strengths = {
        "v": weighted_strength(evidence_item, "virtue"),
        "d": weighted_strength(evidence_item, "deficit_vice"),
        "e": weighted_strength(evidence_item, "excess_vice"),
    }
    dominant = max(highs, key=lambda x: (x[1], strengths[x[0]]))[0]
    if dominant != "v" and v >= HIGH_THRESHOLD:
        bh_item["virtue_score"] = max(0, min(v - 1, LOW_MAX))
    if dominant != "d" and d >= HIGH_THRESHOLD:
        bh_item["deficit_vice_score"] = max(0, min(d - 1, LOW_MAX))
    if dominant != "e" and e >= HIGH_THRESHOLD:
        bh_item["excess_vice_score"] = max(0, min(e - 1, LOW_MAX))
    if dominant == "v":
        bh_item["virtue_score"] = min(5, v + 1)
    elif dominant == "d":
        bh_item["deficit_vice_score"] = min(5, d + 1)
    elif dominant == "e":
        bh_item["excess_vice_score"] = min(5, e + 1)
    return bh_item


def enforce_single_high(score_item, evidence_item=None):
    v = int(score_item.get("final_virtue_score", 0))
    d = int(score_item.get("final_deficit_vice_score", 0))
    e = int(score_item.get("final_excess_vice_score", 0))

    if v == UNCERTAINTY_SCORE and d == UNCERTAINTY_SCORE and e == UNCERTAINTY_SCORE:
        return score_item

    highs = []
    if v >= HIGH_THRESHOLD:
        highs.append("v")
    if d >= HIGH_THRESHOLD:
        highs.append("d")
    if e >= HIGH_THRESHOLD:
        highs.append("e")

    if len(highs) == 0:
        return score_item

    if len(highs) == 1:
        dominant = highs[0]
    else:
        strengths = {
            "v": weighted_strength(evidence_item, "virtue") if evidence_item else 0.0,
            "d": weighted_strength(evidence_item, "deficit_vice") if evidence_item else 0.0,
            "e": weighted_strength(evidence_item, "excess_vice") if evidence_item else 0.0,
        }
        tuples = [("v", v), ("d", d), ("e", e)]
        dominant = max(tuples, key=lambda x: (x[1], strengths[x[0]]))[0]

    if dominant != "v":
        score_item["final_virtue_score"] = min(v, LOW_MAX)
    if dominant != "d":
        score_item["final_deficit_vice_score"] = min(d, LOW_MAX)
    if dominant != "e":
        score_item["final_excess_vice_score"] = min(e, LOW_MAX)
    return score_item


def _bool_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return False


def flag_count_for_item(analysis_item):
    total = 0
    for cls in ["virtue", "deficit_vice", "excess_vice"]:
        cls_payload = analysis_item.get(cls, {}) if isinstance(analysis_item, dict) else {}
        flags = cls_payload.get("special_flags", {}) if isinstance(cls_payload, dict) else {}
        if _bool_flag(flags.get("situationalInconsistency", 0)):
            total += 1
        if _bool_flag((flags.get("socialDesirabilityFlags", {}) or {}).get("flag", False)):
            total += 1
        if _bool_flag((flags.get("negativeBehaviorFlags", {}) or {}).get("flag", False)):
            total += 1
    return total


def apply_multi_flag_bias(score_item, analysis_item, evidence_item, use_final_keys=False):
    flag_count = flag_count_for_item(analysis_item)
    if flag_count < 2:
        return score_item

    v_key = "final_virtue_score" if use_final_keys else "virtue_score_adjusted"
    d_key = "final_deficit_vice_score" if use_final_keys else "deficit_vice_score_adjusted"
    e_key = "final_excess_vice_score" if use_final_keys else "excess_vice_score_adjusted"

    v = int(score_item.get(v_key, 0))
    d = int(score_item.get(d_key, 0))
    e = int(score_item.get(e_key, 0))

    score_item[v_key] = max(0, v - 1)

    d_strength = weighted_strength(evidence_item, "deficit_vice")
    e_strength = weighted_strength(evidence_item, "excess_vice")
    d_ev = count_evidence(evidence_item, "deficit_vice")
    e_ev = count_evidence(evidence_item, "excess_vice")

    if d > e:
        dominant = "deficit_vice"
    elif e > d:
        dominant = "excess_vice"
    else:
        dominant = "deficit_vice" if d_strength >= e_strength else "excess_vice"

    if dominant == "deficit_vice" and d_ev > 0:
        score_item[d_key] = min(5, d + 1)
    if dominant == "excess_vice" and e_ev > 0:
        score_item[e_key] = min(5, e + 1)
    return score_item


def zero_adjustment_for_missing_evidence(adj, evidence_item):
    if count_evidence(evidence_item, "virtue") == 0:
        adj["virtue_score_adjusted"] = 0
    if count_evidence(evidence_item, "deficit_vice") == 0:
        adj["deficit_vice_score_adjusted"] = 0
    if count_evidence(evidence_item, "excess_vice") == 0:
        adj["excess_vice_score_adjusted"] = 0
    return apply_strength_cap(
        adj,
        evidence_item,
        {
            "virtue": "virtue_score_adjusted",
            "deficit_vice": "deficit_vice_score_adjusted",
            "excess_vice": "excess_vice_score_adjusted",
        },
    )


def zero_coordinator_for_missing_evidence(co, evidence_item):
    if count_evidence(evidence_item, "virtue") == 0:
        co["final_virtue_score"] = 0
    if count_evidence(evidence_item, "deficit_vice") == 0:
        co["final_deficit_vice_score"] = 0
    if count_evidence(evidence_item, "excess_vice") == 0:
        co["final_excess_vice_score"] = 0
    # If every class is empty, force uncertain dominant — never leave a phantom high
    if (
        count_evidence(evidence_item, "virtue") == 0
        and count_evidence(evidence_item, "deficit_vice") == 0
        and count_evidence(evidence_item, "excess_vice") == 0
    ):
        co["final_virtue_score"] = 0
        co["final_deficit_vice_score"] = 0
        co["final_excess_vice_score"] = 0
        co["dominant_class"] = "uncertain"
        if not (co.get("arbitration_reasoning") or "").strip():
            co["arbitration_reasoning"] = "No evidence for any class; scores set to 0."
    return co


def finalize_coordinator_item(co, analysis_item, evidence_item):
    # Zero empty classes first so downstream bias / single-high never revive them
    co = zero_coordinator_for_missing_evidence(co, evidence_item)
    co = apply_multi_flag_bias(co, analysis_item, evidence_item, use_final_keys=True)
    co = apply_strength_cap(
        co,
        evidence_item,
        {
            "virtue": "final_virtue_score",
            "deficit_vice": "final_deficit_vice_score",
            "excess_vice": "final_excess_vice_score",
        },
    )
    co = enforce_single_high(co, evidence_item)
    return zero_coordinator_for_missing_evidence(co, evidence_item)
