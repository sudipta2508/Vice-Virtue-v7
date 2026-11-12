from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class MessageRequest(BaseModel):
    content: str


class SessionResponse(BaseModel):
    id: str
    chat_phase: str
    followup_phase: Optional[str]
    ui_screen: str
    messages: list[dict[str, str]]
    progress: dict[str, Any]
    show_results: bool
    has_baseline: bool
    has_refined: bool
    chat_input_enabled: bool = True
    quick_replies: list[str] = []
    model: str
    elapsed: Optional[float]
    token_usage: Optional[dict]
    followup_token_usage: Optional[dict]


class ResultsResponse(BaseModel):
    baseline: Optional[dict]
    refined: Optional[dict]
    mode: str  # "single" | "dual"
