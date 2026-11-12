"""Follow-up flow unit tests (no live Claude)."""

import asyncio

from followup_logic import (
    advance_to_next_dimension_question,
    dimension_consent_prompt,
    dimension_question,
    order_gap_dimensions,
)
from graph.session_graph import _node_followup


def test_order_gap_dimensions_judgment_first():
    assert order_gap_dimensions(["Courage", "Judgment", "Drive"]) == [
        "Judgment",
        "Drive",
        "Courage",
    ]
    assert order_gap_dimensions(["Courage", "Drive"]) == ["Drive", "Courage"]
    assert order_gap_dimensions(["Zebra", "Judgment"]) == ["Judgment", "Zebra"]


def test_dimension_prompts_omit_item_names():
    catalog = {
        "Judgment": [
            {"virtue": "Situational Awareness"},
            {"virtue": "Cognitive Complexity"},
        ],
        "Courage": [{"virtue": "Bravery"}, {"virtue": "Resilience"}],
    }
    for dim, items in catalog.items():
        q = dimension_question(dim, catalog=catalog, evidence={})
        c = dimension_consent_prompt(dim)
        assert dim in q
        assert dim in c
        for it in items:
            assert it["virtue"] not in q
            assert it["virtue"] not in c
        assert "Reply **yes** or **no**" in c


def test_advance_starts_at_dim_consent():
    session = {
        "followup_queue": ["Judgment", "Courage"],
        "followup_asked": [],
        "followup_pending_dim": None,
    }
    msgs = advance_to_next_dimension_question(session)
    assert session["followup_phase"] == "await_dim_consent"
    assert session["followup_pending_dim"] == "Judgment"
    assert "Judgment" in msgs[0]["content"]
    assert "Would you like to tell me more" in msgs[0]["content"]


def test_node_followup_consent_skip_and_accept():
    """Judgment consent no → Courage consent yes → open question (no item names)."""
    from api.session_store import store

    session = store.create()
    session["api_key"] = "sk-test-key-not-used"
    session["chat_phase"] = "active"
    session["followup_phase"] = "await_dim_consent"
    session["followup_queue"] = ["Judgment", "Courage"]
    session["followup_asked"] = ["Judgment"]
    session["followup_pending_dim"] = "Judgment"
    session["out_baseline"] = {"evidence": {}}
    session["out_working"] = {"evidence": {"Judgment": {}, "Courage": {}}}
    session["messages"] = []

    async def _run():
        # Decline Judgment → advance to Courage consent
        await _node_followup(
            {"session_id": session["id"], "user_text": "no", "chat_phase": "active"}
        )
        assert session["followup_phase"] == "await_dim_consent"
        assert session["followup_pending_dim"] == "Courage"
        msgs = [m["content"] for m in session["messages"] if m["role"] == "assistant"]
        assert any("Courage" in m and "Would you like to tell me more" in m for m in msgs)

        # Accept Courage → open question without item names
        session["messages"] = []
        await _node_followup(
            {"session_id": session["id"], "user_text": "yes", "chat_phase": "active"}
        )
        assert session["followup_phase"] == "await_dimension_answer"
        msgs = [m["content"] for m in session["messages"] if m["role"] == "assistant"]
        assert any("Can you tell me more about your **Courage**" in m for m in msgs)
        for it in store.catalog.get("Courage", []):
            assert all(it["virtue"] not in m for m in msgs)

    asyncio.run(_run())


def test_global_consent_orders_queue():
    from api.session_store import store
    from unittest.mock import patch

    session = store.create()
    session["api_key"] = "sk-test"
    session["chat_phase"] = "active"
    session["followup_phase"] = "await_consent"
    session["out_baseline"] = {"evidence": {}}
    session["out_working"] = {"evidence": {}}
    session["messages"] = []

    async def _run():
        with patch(
            "graph.session_graph.build_followup_queue",
            return_value=["Courage", "Judgment"],
        ):
            await _node_followup(
                {"session_id": session["id"], "user_text": "yes", "chat_phase": "active"}
            )
        assert session["followup_queue"] == ["Judgment", "Courage"]
        assert session["followup_phase"] == "await_dim_consent"
        assert session["followup_pending_dim"] == "Judgment"

    asyncio.run(_run())
