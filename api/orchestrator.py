"""Session orchestrator — thin FastAPI adapter over the LangGraph session graph."""

from __future__ import annotations

from typing import Any

from graph.session_graph import handle_message as graph_handle_message


async def handle_message(session_id: str, user_text: str) -> dict[str, Any]:
    """Process a user message; may schedule background assessment / reassessment tasks."""
    return await graph_handle_message(session_id, user_text)
