"""Gap detection unit tests — coverage-below-70% rule."""

from gap_detection import (
    build_gap_queue,
    dimension_coverage,
    item_has_no_evidence,
    item_is_addressed,
    needs_followup,
)
from followup_logic import parse_consent_reply


def _empty():
    return {"virtue_evidences": [], "deficit_vice_evidences": [], "excess_vice_evidences": []}


def _snip(tier=None, text="x"):
    d = {"evidence_id": 1, "text": text, "source_position": "p1"}
    if tier is not None:
        d["strength_tier"] = tier
        d["weight"] = 1.0 if tier != "weak" else 0.3
    return d


def test_item_has_no_evidence():
    assert item_has_no_evidence({}) is True
    assert item_has_no_evidence(_empty())
    assert (
        item_has_no_evidence(
            {
                "virtue_evidences": [{"text": "x"}],
                "deficit_vice_evidences": [],
                "excess_vice_evidences": [],
            }
        )
        is False
    )


def test_item_is_addressed_tiers():
    weak_only = {
        "virtue_evidences": [_snip("weak"), _snip("weak"), _snip("weak"), _snip("weak")],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(weak_only) is False

    explicit = {
        "virtue_evidences": [_snip("explicit")],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(explicit) is True

    strong = {
        "virtue_evidences": [],
        "deficit_vice_evidences": [_snip("strong_implicit")],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(strong) is True

    # Missing tier → fallback strong_implicit → addressed
    bare = {
        "virtue_evidences": [{"text": "x"}],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(bare) is True


def test_build_gap_queue_coverage_threshold():
    catalog = {
        "Courage": [{"virtue": f"I{i}"} for i in range(10)],
    }
    strong = {
        "virtue_evidences": [_snip("explicit")],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    weak = {
        "virtue_evidences": [_snip("weak")],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }

    # 6 of 10 addressed → coverage 0.6 < 0.70 → gap
    evidence_gap = {
        "Courage": {
            **{f"I{i}": strong for i in range(6)},
            **{f"I{i}": weak for i in range(6, 10)},
        }
    }
    assert dimension_coverage(evidence_gap["Courage"], catalog["Courage"]) == 0.6
    assert build_gap_queue(evidence_gap, catalog, threshold=0.70) == ["Courage"]
    assert needs_followup(evidence_gap, catalog, threshold=0.70) is True

    # 7 of 10 addressed → coverage 0.7 not below 0.70 → no gap
    evidence_ok = {
        "Courage": {
            **{f"I{i}": strong for i in range(7)},
            **{f"I{i}": weak for i in range(7, 10)},
        }
    }
    assert dimension_coverage(evidence_ok["Courage"], catalog["Courage"]) == 0.7
    assert build_gap_queue(evidence_ok, catalog, threshold=0.70) == []
    assert needs_followup(evidence_ok, catalog, threshold=0.70) is False


def test_parse_consent_loose():
    assert parse_consent_reply("Yes") == "yes"
    assert parse_consent_reply("yep!") == "yes"
    assert parse_consent_reply("sounds good") == "yes"
    assert parse_consent_reply("No") == "no"
    assert parse_consent_reply("skip") == "no"
    assert parse_consent_reply("I'm good") == "no"
    assert parse_consent_reply("maybe later tomorrow") is None
