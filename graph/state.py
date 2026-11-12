"""Typed state for LangGraph session + assessment workflows."""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class TokenUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int


class Progress(TypedDict, total=False):
    stage: Optional[str]
    percent: float
    message: str


class AssessmentState(TypedDict, total=False):
    """State for the 5-stage assessment graph."""

    api_key: str
    model: str
    catalog: dict
    narrative: str
    paragraphs: dict
    dimensions: list
    evidence: dict
    behavioral_hierarchy: dict
    analysis: dict
    scoring: dict
    adjustment: dict
    coordinator: dict
    token_usage: TokenUsage
    error: Optional[str]


class ReassessmentState(TypedDict, total=False):
    """State for targeted reassessment (stages 2–5 for selected items)."""

    api_key: str
    model: str
    catalog: dict
    working_out: dict
    targets: dict  # {dimension: [item_key, ...]}
    token_usage: TokenUsage
    error: Optional[str]


class SessionState(TypedDict, total=False):
    """Conversation + follow-up session state (maps to session_store fields)."""

    session_id: str
    chat_phase: str
    followup_phase: Optional[str]
    messages: list
    api_key: Optional[str]
    model: str
    narrative: Optional[str]
    progress: Progress
    out_baseline: Optional[dict]
    out_working: Optional[dict]
    out_final: Optional[dict]
    elapsed: Optional[float]
    token_usage: Optional[TokenUsage]
    followup_token_usage: Optional[TokenUsage]
    followup_gap_dims: list
    followup_queue: list
    followup_asked: list
    followup_audit: list
    followup_reassess_targets: dict
    followup_pending_dim: Optional[str]
    pre_additions: list
    pre_optional_pending_dim: Optional[str]
    user_text: str  # latest inbound message
    catalog: dict
