"""Unit tests for no-evidence scoring rules (no live Claude calls)."""

from utils.item_postprocess import (
    apply_no_evidence_rule,
    enforce_bh_single_high,
    finalize_coordinator_item,
    zero_bh_for_missing_evidence,
    zero_coordinator_for_missing_evidence,
)


EMPTY = {
    "virtue_evidences": [],
    "deficit_vice_evidences": [],
    "excess_vice_evidences": [],
}


def test_apply_no_evidence_rule_zeros_all():
    scores = {"virtue_score": 4, "deficit_vice_score": 3, "excess_vice_score": 2}
    out = apply_no_evidence_rule(scores, EMPTY)
    assert out["virtue_score"] == 0
    assert out["deficit_vice_score"] == 0
    assert out["excess_vice_score"] == 0


def test_bh_empty_evidence_never_stays_at_three():
    bh = {"virtue_score": 3, "deficit_vice_score": 3, "excess_vice_score": 3, "reasoning": "x"}
    out = enforce_bh_single_high(bh, EMPTY)
    assert out["virtue_score"] == 0
    assert out["deficit_vice_score"] == 0
    assert out["excess_vice_score"] == 0


def test_zero_bh_partial_evidence():
    evidence = {
        "virtue_evidences": [{"evidence_id": 1, "text": "did X", "source_position": "p1"}],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    bh = {"virtue_score": 4, "deficit_vice_score": 3, "excess_vice_score": 2}
    out = zero_bh_for_missing_evidence(bh, evidence)
    assert out["virtue_score"] == 4
    assert out["deficit_vice_score"] == 0
    assert out["excess_vice_score"] == 0


def test_coordinator_empty_evidence_uncertain():
    co = {
        "final_virtue_score": 3,
        "final_deficit_vice_score": 3,
        "final_excess_vice_score": 3,
        "dominant_class": "virtue",
        "arbitration_reasoning": "",
    }
    out = zero_coordinator_for_missing_evidence(co, EMPTY)
    assert out["final_virtue_score"] == 0
    assert out["final_deficit_vice_score"] == 0
    assert out["final_excess_vice_score"] == 0
    assert out["dominant_class"] == "uncertain"


def test_finalize_does_not_revive_empty_scores():
    co = {
        "final_virtue_score": 4,
        "final_deficit_vice_score": 4,
        "final_excess_vice_score": 0,
        "dominant_class": "virtue",
        "arbitration_reasoning": "conflict",
    }
    analysis = {
        "virtue": {
            "special_flags": {
                "situationalInconsistency": 1,
                "socialDesirabilityFlags": {"flag": True, "reasoning": "x"},
                "negativeBehaviorFlags": {"flag": False, "reasoning": ""},
            }
        },
        "deficit_vice": {},
        "excess_vice": {},
    }
    out = finalize_coordinator_item(co, analysis, EMPTY)
    assert out["final_virtue_score"] == 0
    assert out["final_deficit_vice_score"] == 0
    assert out["final_excess_vice_score"] == 0
