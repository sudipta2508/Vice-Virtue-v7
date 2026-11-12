"""Evidence strength tier unit tests (no live Claude calls)."""

from gap_detection import build_gap_queue, item_is_addressed
from graph.evidence_tiers import (
    merge_tiers,
    normalize_tier,
    tier_weight,
    weighted_strength,
)
from utils.item_postprocess import (
    apply_multi_flag_bias,
    apply_strength_cap,
    enforce_bh_single_high,
    enforce_single_high,
)


def _ev(tier=None, weight=None, eid=1, text="snippet"):
    d = {"evidence_id": eid, "text": text, "source_position": "p1"}
    if tier is not None:
        d["strength_tier"] = tier
    if weight is not None:
        d["weight"] = weight
    return d


def test_normalize_tier_aliases():
    assert normalize_tier("explicit") == "explicit"
    assert normalize_tier("Strong-Implicit") == "strong_implicit"
    assert normalize_tier("WEAK") == "weak"
    assert normalize_tier("bogus") == "strong_implicit"
    assert normalize_tier(None) == "strong_implicit"


def test_merge_tiers_valid_and_fallback():
    evidence = {
        "Honesty": {
            "virtue_evidences": [_ev(eid=1), _ev(eid=2), _ev(eid=3)],
            "deficit_vice_evidences": [],
            "excess_vice_evidences": [],
        }
    }
    tiers = {
        "Honesty": {
            "tiers": [
                {
                    "evidence_id": 1,
                    "cls": "virtue",
                    "strength_tier": "explicit",
                    "tier_reasoning": "Names honesty.",
                },
                {
                    "evidence_id": 2,
                    "cls": "virtue",
                    "strength_tier": "invalid_label",
                    "tier_reasoning": "bad",
                },
                # 3 missing — fallback
            ]
        }
    }
    out = merge_tiers(evidence, tiers)
    snips = out["Honesty"]["virtue_evidences"]
    assert snips[0]["strength_tier"] == "explicit"
    assert snips[0]["weight"] == 1.0
    assert snips[1]["strength_tier"] == "strong_implicit"  # invalid → fallback
    assert snips[1]["weight"] == 1.0
    assert snips[2]["strength_tier"] == "strong_implicit"  # missing → fallback
    assert snips[2]["weight"] == 1.0


def test_weighted_strength_sums():
    item = {
        "virtue_evidences": [
            _ev(tier="explicit", weight=1.0, eid=1),
            _ev(tier="weak", weight=0.3, eid=2),
            _ev(tier="weak", weight=0.3, eid=3),
        ],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert weighted_strength(item, "virtue") == 1.6
    assert weighted_strength(item, "deficit_vice") == 0.0
    # Missing weight uses fallback (strong_implicit = 1.0)
    bare = {"virtue_evidences": [{"text": "x"}], "deficit_vice_evidences": [], "excess_vice_evidences": []}
    assert weighted_strength(bare, "virtue") == 1.0


def test_strength_cap_weak_only():
    # One weak snippet → strength 0.3 < 1.0 → cap at 3
    evidence = {
        "virtue_evidences": [_ev(tier="weak", weight=0.3)],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    scores = {"virtue_score": 5, "deficit_vice_score": 0, "excess_vice_score": 0}
    out = apply_strength_cap(
        scores,
        evidence,
        {
            "virtue": "virtue_score",
            "deficit_vice": "deficit_vice_score",
            "excess_vice": "excess_vice_score",
        },
    )
    assert out["virtue_score"] == 3

    # Four weak snippets → 1.2 >= 1.0 → no cap
    evidence4 = {
        "virtue_evidences": [_ev(tier="weak", weight=0.3, eid=i) for i in range(4)],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    scores4 = {"virtue_score": 5, "deficit_vice_score": 0, "excess_vice_score": 0}
    out4 = apply_strength_cap(
        scores4,
        evidence4,
        {
            "virtue": "virtue_score",
            "deficit_vice": "deficit_vice_score",
            "excess_vice": "excess_vice_score",
        },
    )
    assert out4["virtue_score"] == 5


def test_gap_weak_only_counts_as_gap():
    weak_only = {
        "virtue_evidences": [_ev(tier="weak", weight=0.3)],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(weak_only) is False

    strong = {
        "virtue_evidences": [_ev(tier="explicit", weight=1.0)],
        "deficit_vice_evidences": [],
        "excess_vice_evidences": [],
    }
    assert item_is_addressed(strong) is True

    catalog = {
        "Courage": [{"virtue": f"I{i}"} for i in range(10)],
    }
    # 2 strong + 8 weak → coverage 0.2 < 0.70 → gap
    evidence = {
        "Courage": {
            **{f"I{i}": weak_only for i in range(8)},
            "I8": strong,
            "I9": strong,
        }
    }
    assert build_gap_queue(evidence, catalog, threshold=0.70) == ["Courage"]


def test_tiebreak_uses_weighted_strength():
    # BH: virtue=4 and deficit=4; deficit has stronger weighted evidence → deficit wins
    evidence = {
        "virtue_evidences": [_ev(tier="weak", weight=0.3, eid=1)],
        "deficit_vice_evidences": [
            _ev(tier="explicit", weight=1.0, eid=2),
            _ev(tier="explicit", weight=1.0, eid=3),
        ],
        "excess_vice_evidences": [],
    }
    bh = {"virtue_score": 4, "deficit_vice_score": 4, "excess_vice_score": 0}
    out = enforce_bh_single_high(bh, evidence)
    assert out["deficit_vice_score"] >= 4
    assert out["virtue_score"] <= 2

    # Coordinator single-high: same scores, virtue weaker → deficit wins
    co = {
        "final_virtue_score": 4,
        "final_deficit_vice_score": 4,
        "final_excess_vice_score": 0,
    }
    out_co = enforce_single_high(co, evidence)
    assert out_co["final_deficit_vice_score"] == 4
    assert out_co["final_virtue_score"] == 2

    # Multi-flag bias: tied vice scores → stronger excess wins
    evidence2 = {
        "virtue_evidences": [_ev(tier="explicit", weight=1.0)],
        "deficit_vice_evidences": [_ev(tier="weak", weight=0.3, eid=10)],
        "excess_vice_evidences": [
            _ev(tier="explicit", weight=1.0, eid=11),
            _ev(tier="explicit", weight=1.0, eid=12),
        ],
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
    scores = {
        "final_virtue_score": 4,
        "final_deficit_vice_score": 2,
        "final_excess_vice_score": 2,
    }
    out_bias = apply_multi_flag_bias(scores, analysis, evidence2, use_final_keys=True)
    assert out_bias["final_virtue_score"] == 3
    assert out_bias["final_excess_vice_score"] == 3
    assert out_bias["final_deficit_vice_score"] == 2


def test_tier_weight_lookup():
    assert tier_weight("explicit") == 1.0
    assert tier_weight("strong_implicit") == 1.0
    assert tier_weight("weak") == 0.3
    assert tier_weight("unknown") == 1.0  # fallback
