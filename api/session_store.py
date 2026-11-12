"""In-memory session store."""

from __future__ import annotations

import copy
import uuid
from typing import Any, Optional

from config import DEFAULT_MODEL, load_item_catalog_from_xlsx

API_KEY_PROMPT = (
    "Welcome to the **Leader Character** assessment chatbot.\n\n"
    "To get started, please enter your **Claude API key** (it will stay in this session only)."
)

NARRATIVE_PROMPT = (
    "Please tell me about your **leader character journey** — share experiences, moments, and situations "
    "that show how you lead, including challenges or times when you struggled."
)


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._catalog = load_item_catalog_from_xlsx()

    @property
    def catalog(self) -> dict:
        return self._catalog

    def create(self) -> dict:
        sid = str(uuid.uuid4())
        session = {
            "id": sid,
            "chat_phase": "await_api_key",
            "followup_phase": None,
            "messages": [{"role": "assistant", "content": API_KEY_PROMPT}],
            "api_key": None,
            "model": DEFAULT_MODEL,
            "narrative": None,
            "progress": {"stage": None, "percent": 0.0, "message": ""},
            "out_baseline": None,
            "out_working": None,
            "out_final": None,
            "elapsed": None,
            "token_usage": None,
            "followup_token_usage": None,
            "followup_gap_dims": [],
            "followup_queue": [],
            "followup_asked": [],
            "followup_audit": [],
            "followup_reassess_targets": {},
            "followup_pending_dim": None,
            "pre_additions": [],
            "pre_optional_pending_dim": None,
            "gap_threshold": None,  # defaults to config.GAP_THRESHOLD when None
            "_task": None,
        }
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def public_view(self, session: dict) -> dict:
        """Session state safe for API responses (no api_key)."""
        followup = session.get("followup_phase")
        chat_phase = session.get("chat_phase")

        pre_baseline_chat = (
            "await_pre_add_more_consent",
            "await_pre_optional_dimension",
            "await_pre_optional_narrative",
            "await_pre_add_more_again",
        )
        chat_only_followup = (
            "await_consent",
            "await_dim_consent",
            "await_dimension_answer",
            "await_gap_dim_add_more",
            "await_gap_dim_more_text",
            "reassessing",
        )

        ui_screen = "chat"
        if chat_phase in (
            "await_api_key",
            "await_narrative",
            *pre_baseline_chat,
            "analyzing",
        ):
            ui_screen = "chat"
        elif followup in chat_only_followup:
            ui_screen = "chat"
        elif followup == "complete" and session.get("followup_audit"):
            ui_screen = "results_with_followup"
        elif followup in ("skipped_no_gaps", "declined", "complete"):
            ui_screen = "results_no_followup"
        elif session.get("out_baseline") and chat_phase == "active":
            if followup in (None, *chat_only_followup):
                ui_screen = "chat"
            else:
                ui_screen = "results_no_followup"

        show_results = ui_screen.startswith("results_")
        has_baseline = session.get("out_baseline") is not None
        has_refined = (
            followup == "complete"
            and bool(session.get("followup_audit"))
            and session.get("out_final") is not None
        )
        chat_input_enabled = chat_phase not in ("analyzing",) and followup not in ("reassessing",)

        # Yes / No / Skip quick replies for consent and add-more turns
        quick_replies: list[str] = []
        yes_no_phases = {
            "await_pre_add_more_consent",
            "await_pre_add_more_again",
        }
        yes_no_followup = {
            "await_consent",
            "await_dim_consent",
            "await_gap_dim_add_more",
        }
        if chat_phase in yes_no_phases or followup in yes_no_followup:
            quick_replies = ["Yes", "No", "Skip"]

        return {
            "id": session["id"],
            "chat_phase": chat_phase,
            "followup_phase": followup,
            "ui_screen": ui_screen,
            "messages": list(session.get("messages", [])),
            "progress": dict(session.get("progress", {})),
            "show_results": show_results,
            "has_baseline": has_baseline,
            "has_refined": has_refined,
            "chat_input_enabled": chat_input_enabled,
            "quick_replies": quick_replies,
            "model": session.get("model", DEFAULT_MODEL),
            "elapsed": session.get("elapsed"),
            "token_usage": session.get("token_usage"),
            "followup_token_usage": session.get("followup_token_usage"),
        }


store = SessionStore()
