"""Clarification evidence extraction via ChatAnthropic (follow-up answers)."""

from __future__ import annotations

from config import CLASSIFICATION_MAX_TOKENS, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from followup_evidence import normalize_dimension_evidence
from graph.evidence_tiers import classify_evidence_tiers
from graph.llm import make_llm
from utils.prompts import create_dimension_clarification_evidence_prompt


async def extract_clarification_evidence(
    api_key: str,
    model: str,
    dimension: str,
    items: list,
    user_answer: str,
    session: dict,
) -> dict:
    llm = make_llm(api_key, model, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE)
    raw = await llm.ainvoke_json(
        create_dimension_clarification_evidence_prompt(dimension, items, user_answer),
        max_tokens_override=CLASSIFICATION_MAX_TOKENS,
    )
    usage = session.setdefault("followup_token_usage", {"input_tokens": 0, "output_tokens": 0})
    usage["input_tokens"] += llm.total_input_tokens
    usage["output_tokens"] += llm.total_output_tokens
    evidence_dim = normalize_dimension_evidence(raw, dimension)
    # Stage 1b — tier new follow-up snippets before merge / reassessment
    evidence_dim = await classify_evidence_tiers(
        api_key, dimension, items, evidence_dim, usage, narrative=None
    )
    return evidence_dim
