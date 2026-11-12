"""LangGraph session conversation graph — replaces api/orchestrator phase machine.

Each user message is one ainvoke turn. Routing is driven by chat_phase / followup_phase
stored in session_store (and mirrored into SessionState). Long-running baseline and
reassessment still run as background asyncio tasks so the UI can poll progress.
"""

from __future__ import annotations

import asyncio
import copy
import time
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from config import DEFAULT_MODEL, GAP_THRESHOLD
from followup_logic import (
    ADD_MORE_AGAIN_MESSAGE,
    ADD_MORE_CONSENT_MESSAGE,
    AMBIGUOUS_YES_NO_MESSAGE,
    advance_to_next_dimension_question,
    build_combined_narrative,
    dimension_question,
    gap_dimension_add_more_prompt,
    init_followup_state,
    looks_like_api_key,
    match_dimension_from_text,
    optional_dimension_prompt,
    optional_narrative_prompt,
    order_gap_dimensions,
    parse_wants_to_end,
    parse_yes_no,
    process_dimension_answer,
    run_final_reassessment,
)
from gap_detection import build_followup_queue
from graph.assessment_graph import run_async_analysis
from graph.checkpointer import get_checkpointer
from graph.state import SessionState
from api.session_store import NARRATIVE_PROMPT, store

ANALYSIS_STARTED_MSG = (
    "Thank you for sharing your journey. I'm analyzing your narrative now — "
    "this may take several minutes. Please wait…"
)


def _append(session: dict, role: str, content: str):
    session.setdefault("messages", []).append({"role": role, "content": content})


def _set_progress(session: dict, stage: str, percent: float, message: str):
    session["progress"] = {"stage": stage, "percent": percent, "message": message}


def _start_baseline_analysis(session: dict, session_id: str):
    combined = build_combined_narrative(
        session.get("narrative") or "",
        session.get("pre_additions") or [],
    )
    session["chat_phase"] = "analyzing"
    _append(session, "assistant", ANALYSIS_STARTED_MSG)
    _set_progress(session, "stage1", 0.0, "Starting analysis…")
    # Do NOT wipe the whole cache folder — CACHE_POLICY=narrative_hash reuses stage results
    asyncio.create_task(_run_baseline_task(session_id, combined))


async def _run_baseline_task(session_id: str, narrative: str):
    session = store.get(session_id)
    if not session:
        return

    api_key = session.get("api_key", "")
    model = session.get("model", DEFAULT_MODEL)
    catalog = store.catalog

    def on_progress(stage: str, percent: float, message: str):
        s = store.get(session_id)
        if s:
            _set_progress(s, stage, percent, message)

    start = time.time()
    try:
        out = await run_async_analysis(
            api_key, model, dict(catalog), narrative, on_progress=on_progress
        )
    except Exception as exc:
        s = store.get(session_id)
        if s:
            s["chat_phase"] = "await_narrative"
            _append(
                s,
                "assistant",
                f"Analysis failed: {exc}\n\nPlease try sending your narrative again, or check your API key.",
            )
            _set_progress(s, "error", 0.0, str(exc))
        return

    s = store.get(session_id)
    if not s:
        return

    elapsed = time.time() - start
    token_usage = out.pop("token_usage", {"input_tokens": 0, "output_tokens": 0})
    out_baseline = copy.deepcopy(out)
    s["out_baseline"] = out_baseline
    s["out_working"] = copy.deepcopy(out)
    s["elapsed"] = elapsed
    s["token_usage"] = token_usage
    s["chat_phase"] = "active"
    _set_progress(s, "done", 1.0, f"Analysis complete in {elapsed:.1f}s")
    _append(s, "assistant", f"Initial analysis finished in {elapsed:.1f} seconds.")

    followup_msgs = init_followup_state(s, catalog, out_baseline)
    for msg in followup_msgs:
        _append(s, msg["role"], msg["content"])


async def _run_reassessment_task(session_id: str, closing_message: str):
    session = store.get(session_id)
    if not session:
        return

    api_key = session.get("api_key", "")
    model = session.get("model", DEFAULT_MODEL)
    catalog = store.catalog
    working_out = session.get("out_working")

    def on_progress(stage: str, percent: float, message: str):
        s = store.get(session_id)
        if s:
            _set_progress(s, stage, percent, message)

    _append(session, "assistant", "Reassessing items with new evidence…")
    session["followup_phase"] = "reassessing"
    _set_progress(session, "reassessing", 0.1, "Reassessing items with new evidence…")

    await run_final_reassessment(
        api_key, model, catalog, working_out, session, on_progress=on_progress
    )

    s = store.get(session_id)
    if not s:
        return

    s["out_final"] = working_out
    s["followup_phase"] = "complete"
    s["followup_pending_dim"] = None
    _set_progress(s, "done", 1.0, "Reassessment complete")
    _append(s, "assistant", closing_message)


def _finish_gap_dimension_or_advance(session: dict, session_id: str):
    for msg in advance_to_next_dimension_question(session, catalog=store.catalog):
        _append(session, msg["role"], msg["content"])
    if session.get("followup_phase") == "reassessing":
        asyncio.create_task(
            _run_reassessment_task(
                session_id,
                "Follow-up complete. Your baseline and refined results are ready.",
            )
        )


# ---- Graph nodes (operate on session_store via session_id) ----


def _route(state: SessionState) -> str:
    session = store.get(state["session_id"])
    if not session:
        return "done"
    if session.get("chat_phase") == "analyzing":
        return "analyzing"
    if session.get("out_baseline"):
        return "followup"
    phase = session.get("chat_phase") or "await_api_key"
    if phase == "await_api_key":
        return "api_key"
    if phase == "await_narrative":
        return "narrative"
    if str(phase).startswith("await_pre_"):
        return "pre_baseline"
    return "done"


async def _node_api_key(state: SessionState) -> dict:
    session = store.get(state["session_id"])
    text = state.get("user_text") or ""
    if not looks_like_api_key(text):
        _append(
            session,
            "assistant",
            "That doesn't look like a valid API key. Please paste your Claude API key "
            "(usually starts with `sk-ant-`).",
        )
        return {}
    session["api_key"] = text.strip()
    session["chat_phase"] = "await_narrative"
    session["messages"] = [{"role": "assistant", "content": NARRATIVE_PROMPT}]
    return {}


async def _node_narrative(state: SessionState) -> dict:
    session = store.get(state["session_id"])
    narrative = (state.get("user_text") or "").strip()
    if len(narrative) < 80:
        _append(
            session,
            "assistant",
            "Please share a bit more about your leader character journey "
            "(at least a few sentences) so the assessment can be meaningful.",
        )
        return {}
    session["narrative"] = narrative
    session.setdefault("pre_additions", [])
    session.setdefault("gap_threshold", GAP_THRESHOLD)
    session["chat_phase"] = "await_pre_add_more_consent"
    _append(session, "assistant", ADD_MORE_CONSENT_MESSAGE)
    return {}


async def _node_pre_baseline(state: SessionState) -> dict:
    session = store.get(state["session_id"])
    user_text = state.get("user_text") or ""
    chat_phase = session.get("chat_phase", "")
    catalog = store.catalog
    session_id = session["id"]

    if parse_wants_to_end(user_text):
        _start_baseline_analysis(session, session_id)
        return {}

    if chat_phase == "await_pre_add_more_consent":
        reply = parse_yes_no(user_text)
        if reply == "no":
            _start_baseline_analysis(session, session_id)
            return {}
        if reply == "yes":
            session["chat_phase"] = "await_pre_optional_dimension"
            session["pre_optional_pending_dim"] = None
            _append(session, "assistant", optional_dimension_prompt(catalog))
            return {}
        _append(session, "assistant", AMBIGUOUS_YES_NO_MESSAGE)
        return {}

    if chat_phase == "await_pre_optional_dimension":
        dim = match_dimension_from_text(user_text, catalog)
        if not dim:
            _append(
                session,
                "assistant",
                "I didn't recognize that dimension. " + optional_dimension_prompt(catalog),
            )
            return {}
        session["pre_optional_pending_dim"] = dim
        session["chat_phase"] = "await_pre_optional_narrative"
        _append(session, "assistant", optional_narrative_prompt(dim))
        return {}

    if chat_phase == "await_pre_optional_narrative":
        dim = session.get("pre_optional_pending_dim")
        if not dim:
            session["chat_phase"] = "await_pre_optional_dimension"
            _append(session, "assistant", optional_dimension_prompt(catalog))
            return {}
        text = user_text.strip()
        if text:
            session.setdefault("pre_additions", []).append({"dimension": dim, "text": text})
        session["pre_optional_pending_dim"] = None
        session["chat_phase"] = "await_pre_add_more_again"
        _append(session, "assistant", ADD_MORE_AGAIN_MESSAGE)
        return {}

    if chat_phase == "await_pre_add_more_again":
        reply = parse_yes_no(user_text)
        if reply == "no":
            _start_baseline_analysis(session, session_id)
            return {}
        if reply == "yes":
            session["chat_phase"] = "await_pre_optional_dimension"
            _append(session, "assistant", optional_dimension_prompt(catalog))
            return {}
        _append(session, "assistant", AMBIGUOUS_YES_NO_MESSAGE)
        return {}

    return {}


async def _node_analyzing(state: SessionState) -> dict:
    # Ignore messages while analyzing; public_view already disables input
    return {}


async def _node_followup(state: SessionState) -> dict:
    session = store.get(state["session_id"])
    user_text = state.get("user_text") or ""
    phase = session.get("followup_phase", "await_consent")
    working_out = session.get("out_working")
    out_baseline = session.get("out_baseline")
    catalog = store.catalog
    api_key = session.get("api_key", "")
    model = session.get("model", DEFAULT_MODEL)
    session_id = session["id"]

    if not working_out or not out_baseline:
        return {}

    had_answers = bool(session.get("followup_audit"))

    if parse_wants_to_end(user_text):
        if had_answers:
            session["followup_phase"] = "reassessing"
            asyncio.create_task(
                _run_reassessment_task(
                    session_id,
                    "Follow-up ended early. Your baseline and refined results are ready.",
                )
            )
        else:
            session["followup_phase"] = "declined"
            session["out_final"] = working_out
            _append(session, "assistant", "Understood — your baseline results are ready.")
        return {}

    if phase == "await_consent":
        reply = parse_yes_no(user_text)
        if reply == "no":
            session["followup_phase"] = "declined"
            session["out_final"] = working_out
            _append(session, "assistant", "No problem. Your baseline results are ready.")
            return {}
        if reply == "yes":
            threshold = session.get("gap_threshold")
            if threshold is None:
                threshold = GAP_THRESHOLD
            threshold = float(threshold)
            queue = order_gap_dimensions(
                build_followup_queue(
                    working_out.get("evidence", {}), catalog, threshold=threshold
                )
            )
            session["followup_queue"] = queue
            if not queue:
                session["followup_phase"] = "skipped_no_gaps"
                session["out_final"] = working_out
                _append(
                    session,
                    "assistant",
                    "No further questions are needed. Your results are ready.",
                )
                return {}
            _finish_gap_dimension_or_advance(session, session_id)
            return {}
        _append(session, "assistant", AMBIGUOUS_YES_NO_MESSAGE)
        return {}

    if phase == "await_dim_consent":
        reply = parse_yes_no(user_text)
        dim = session.get("followup_pending_dim")
        if reply == "yes":
            if not dim:
                _finish_gap_dimension_or_advance(session, session_id)
                return {}
            session["followup_phase"] = "await_dimension_answer"
            _append(session, "assistant", dimension_question(dim))
            return {}
        if reply == "no":
            _finish_gap_dimension_or_advance(session, session_id)
            return {}
        _append(session, "assistant", AMBIGUOUS_YES_NO_MESSAGE)
        return {}

    if phase == "await_dimension_answer":
        dim = session.get("followup_pending_dim")
        if not dim:
            _finish_gap_dimension_or_advance(session, session_id)
            return {}
        audit = await process_dimension_answer(
            api_key, model, dim, user_text, catalog, working_out, session, source="gap"
        )
        session.setdefault("followup_audit", []).append(audit)
        session["followup_phase"] = "await_gap_dim_add_more"
        _append(session, "assistant", gap_dimension_add_more_prompt(dim))
        return {}

    if phase == "await_gap_dim_add_more":
        reply = parse_yes_no(user_text)
        dim = session.get("followup_pending_dim")
        if reply == "yes":
            session["followup_phase"] = "await_gap_dim_more_text"
            _append(
                session,
                "assistant",
                f"Sure — add anything else about your **{dim}**.",
            )
            return {}
        if reply == "no":
            _finish_gap_dimension_or_advance(session, session_id)
            return {}
        _append(session, "assistant", AMBIGUOUS_YES_NO_MESSAGE)
        return {}

    if phase == "await_gap_dim_more_text":
        dim = session.get("followup_pending_dim")
        if dim and user_text.strip():
            audit = await process_dimension_answer(
                api_key,
                model,
                dim,
                user_text,
                catalog,
                working_out,
                session,
                source="gap_more",
            )
            session.setdefault("followup_audit", []).append(audit)
        session["followup_phase"] = "await_gap_dim_add_more"
        _append(session, "assistant", gap_dimension_add_more_prompt(dim or "this dimension"))
        return {}

    if phase == "reassessing":
        return {}

    return {}


async def _node_done(state: SessionState) -> dict:
    return {}


def build_session_graph():
    g = StateGraph(SessionState)
    g.add_node("api_key", _node_api_key)
    g.add_node("narrative", _node_narrative)
    g.add_node("pre_baseline", _node_pre_baseline)
    g.add_node("analyzing", _node_analyzing)
    g.add_node("followup", _node_followup)
    g.add_node("done", _node_done)

    g.add_conditional_edges(
        START,
        _route,
        {
            "api_key": "api_key",
            "narrative": "narrative",
            "pre_baseline": "pre_baseline",
            "analyzing": "analyzing",
            "followup": "followup",
            "done": "done",
        },
    )
    for node in ("api_key", "narrative", "pre_baseline", "analyzing", "followup", "done"):
        g.add_edge(node, END)

    return g.compile(checkpointer=get_checkpointer())


_SESSION_GRAPH = None


def get_session_graph():
    global _SESSION_GRAPH
    if _SESSION_GRAPH is None:
        _SESSION_GRAPH = build_session_graph()
    return _SESSION_GRAPH


async def handle_message(session_id: str, user_text: str) -> dict[str, Any]:
    """Process a user message via the LangGraph session graph; returns public_view."""
    session = store.get(session_id)
    if not session:
        raise ValueError("Session not found")

    _append(session, "user", user_text)

    graph = get_session_graph()
    config = {"configurable": {"thread_id": session_id}}
    await graph.ainvoke(
        {
            "session_id": session_id,
            "user_text": user_text,
            "catalog": store.catalog,
            "model": session.get("model", DEFAULT_MODEL),
            "chat_phase": session.get("chat_phase"),
            "followup_phase": session.get("followup_phase"),
            "messages": list(session.get("messages") or []),
        },
        config=config,
    )
    return store.public_view(session)
