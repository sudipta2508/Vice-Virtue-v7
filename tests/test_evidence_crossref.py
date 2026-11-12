"""Evidence cross-reference hashtag unit tests (no live Claude)."""

from api.ui_transform import (
    _also_used_for,
    _build_evidence_crossref_index,
    _normalize_evidence_text,
    build_dimension_items,
)


SHARED = "I pushed the team past their limits under pressure."


def test_normalize_evidence_text():
    assert _normalize_evidence_text("  Hello   World \n") == "hello world"
    assert _normalize_evidence_text("") == ""
    assert _normalize_evidence_text(None) == ""


def test_build_dimension_items_also_used():
    catalog = {
        "Temperance": [{"virtue": "Patience"}],
        "Courage": [{"virtue": "Bravery"}],
    }
    output = {
        "evidence": {
            "Temperance": {
                "Patience": {
                    "virtue_evidences": [],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [
                        {
                            "evidence_id": 1,
                            "text": SHARED,
                            "source_position": "paragraph_1",
                            "strength_tier": "explicit",
                            "weight": 1.0,
                        }
                    ],
                }
            },
            "Courage": {
                "Bravery": {
                    "virtue_evidences": [],
                    "deficit_vice_evidences": [
                        {
                            "evidence_id": 3,
                            "text": f"  {SHARED}  ",  # whitespace/case variants still match
                            "source_position": "paragraph_1",
                            "strength_tier": "strong_implicit",
                            "weight": 1.0,
                        }
                    ],
                    "excess_vice_evidences": [],
                }
            },
        },
        "analysis": {},
        "scoring": {},
        "adjustment": {},
        "coordinator": {},
        "behavioral_hierarchy": {},
    }

    temperance_items = build_dimension_items(output, catalog, "Temperance")
    patience = next(it for it in temperance_items if it["virtue"] == "Patience")
    excess = patience["evidence"]["excess_vice"]
    assert len(excess) == 1
    also = excess[0]["also_used"]
    assert also == [{"dimension": "Courage", "item": "Bravery", "cls": "deficit"}]
    # Current location must not appear
    assert {"dimension": "Temperance", "item": "Patience", "cls": "excess"} not in also

    courage_items = build_dimension_items(output, catalog, "Courage")
    bravery = next(it for it in courage_items if it["virtue"] == "Bravery")
    deficit = bravery["evidence"]["deficit_vice"]
    assert deficit[0]["also_used"] == [
        {"dimension": "Temperance", "item": "Patience", "cls": "excess"}
    ]


def test_also_used_empty_when_unique():
    catalog = {"Drive": [{"virtue": "Passion"}]}
    output = {
        "evidence": {
            "Drive": {
                "Passion": {
                    "virtue_evidences": [{"evidence_id": 1, "text": "unique snippet only here"}],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [],
                }
            }
        }
    }
    index = _build_evidence_crossref_index(output, catalog)
    assert _also_used_for(index, "unique snippet only here", "Drive", "Passion", "virtue") == []
