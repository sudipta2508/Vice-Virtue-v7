"""Dimension mean scoring — average only items with evidence for each class."""

from dimension_means import compute_dimension_means


def test_mean_excludes_items_without_evidence():
    catalog = {
        "Courage": [
            {"virtue": "A"},
            {"virtue": "B"},
            {"virtue": "C"},
            {"virtue": "D"},
            {"virtue": "E"},
        ]
    }
    output = {
        "evidence": {
            "Courage": {
                "A": {
                    "virtue_evidences": [{"text": "a"}],
                    "deficit_vice_evidences": [{"text": "ad"}],
                    "excess_vice_evidences": [],
                },
                "B": {
                    "virtue_evidences": [{"text": "b"}],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [{"text": "be"}],
                },
                "C": {
                    "virtue_evidences": [{"text": "c"}],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [],
                },
                "D": {
                    "virtue_evidences": [],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [],
                },
                "E": {
                    "virtue_evidences": [],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [],
                },
            }
        },
        "coordinator": {
            "Courage": {
                "A": {
                    "final_virtue_score": 4,
                    "final_deficit_vice_score": 1,
                    "final_excess_vice_score": 0,
                },
                "B": {
                    "final_virtue_score": 3,
                    "final_deficit_vice_score": 0,
                    "final_excess_vice_score": 2,
                },
                "C": {
                    "final_virtue_score": 5,
                    "final_deficit_vice_score": 0,
                    "final_excess_vice_score": 0,
                },
                "D": {
                    "final_virtue_score": 0,
                    "final_deficit_vice_score": 0,
                    "final_excess_vice_score": 0,
                },
                "E": {
                    "final_virtue_score": 0,
                    "final_deficit_vice_score": 0,
                    "final_excess_vice_score": 0,
                },
            }
        },
    }
    means = compute_dimension_means(output, catalog)["Courage"]
    assert means["virtue"] == round((4 + 3 + 5) / 3, 2)
    assert means["deficit_vice"] == 1.0  # only A
    assert means["excess_vice"] == 2.0  # only B
    assert means["item_counts"]["virtue"] == 3
    assert means["item_counts"]["deficit_vice"] == 1
    assert means["item_counts"]["excess_vice"] == 1
    assert means["item_counts"]["total_items"] == 5


def test_mean_none_when_no_evidence_for_class():
    catalog = {"Drive": [{"virtue": "Passion"}]}
    output = {
        "evidence": {
            "Drive": {
                "Passion": {
                    "virtue_evidences": [],
                    "deficit_vice_evidences": [],
                    "excess_vice_evidences": [],
                }
            }
        },
        "coordinator": {
            "Drive": {
                "Passion": {
                    "final_virtue_score": 0,
                    "final_deficit_vice_score": 0,
                    "final_excess_vice_score": 0,
                }
            }
        },
    }
    means = compute_dimension_means(output, catalog)["Drive"]
    assert means["virtue"] is None
    assert means["deficit_vice"] is None
    assert means["excess_vice"] is None
