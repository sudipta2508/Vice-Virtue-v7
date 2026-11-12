"""Graph routing helpers — empty dimensions skip stages 2–5 (no live Claude)."""

from graph.defaults import (
    default_coordinator_item,
    default_score_item,
    dimension_has_any_evidence,
    item_has_any_evidence,
)
from graph.assessment_graph import _stages_2_to_5_dimension
import asyncio


def test_item_has_any_evidence():
    assert item_has_any_evidence({}) is False
    assert (
        item_has_any_evidence(
            {
                "virtue_evidences": [],
                "deficit_vice_evidences": [{"text": "x"}],
                "excess_vice_evidences": [],
            }
        )
        is True
    )


def test_dimension_has_any_evidence():
    items = [{"virtue": "A"}, {"virtue": "B"}]
    empty_dim = {
        "A": {"virtue_evidences": [], "deficit_vice_evidences": [], "excess_vice_evidences": []},
        "B": {"virtue_evidences": [], "deficit_vice_evidences": [], "excess_vice_evidences": []},
    }
    assert dimension_has_any_evidence(empty_dim, items) is False


def test_empty_dimension_skips_llm_and_zeros():
    items = [{"virtue": "A"}, {"virtue": "B"}]
    evidence_dim = {
        "A": {"virtue_evidences": [], "deficit_vice_evidences": [], "excess_vice_evidences": []},
        "B": {"virtue_evidences": [], "deficit_vice_evidences": [], "excess_vice_evidences": []},
    }
    bh_dim = {
        "A": {"virtue_score": 0, "deficit_vice_score": 0, "excess_vice_score": 0},
        "B": {"virtue_score": 0, "deficit_vice_score": 0, "excess_vice_score": 0},
    }
    usage = {"input_tokens": 0, "output_tokens": 0}

    dim, analysis, scoring, adjustment, coordinator = asyncio.run(
        _stages_2_to_5_dimension(
            "Courage",
            items,
            evidence_dim,
            bh_dim,
            narrative="unused",
            api_key="sk-test",
            model="unused",
            usage=usage,
        )
    )

    assert dim == "Courage"
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert scoring["A"] == default_score_item()
    assert coordinator["A"]["final_virtue_score"] == 0
    assert coordinator["A"]["dominant_class"] == "uncertain"
    assert coordinator["B"]["final_virtue_score"] == 0


def test_session_quick_replies_yes_no_phases():
    from api.session_store import SessionStore

    store = SessionStore()
    session = store.create()
    session["chat_phase"] = "await_pre_add_more_consent"
    view = store.public_view(session)
    assert view["quick_replies"] == ["Yes", "No", "Skip"]

    session["chat_phase"] = "active"
    session["followup_phase"] = "await_consent"
    session["out_baseline"] = {"evidence": {}}
    view = store.public_view(session)
    assert view["quick_replies"] == ["Yes", "No", "Skip"]

    session["followup_phase"] = "await_dim_consent"
    view = store.public_view(session)
    assert view["quick_replies"] == ["Yes", "No", "Skip"]

    session["followup_phase"] = "await_dimension_answer"
    view = store.public_view(session)
    assert view["quick_replies"] == []
