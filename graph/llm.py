"""ChatAnthropic JSON helper — replaces agents.base_agent.BaseAgent.

Note: Anthropic SDK 2.8+ MessageCreateParams no longer accepts `temperature`
(passing it raises: \"temperature: Extra inputs are not permitted\").
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage


_MODEL_LIST_CACHE: dict[str, list[str]] = {}
_RESOLVED_MODEL_CACHE: dict[tuple[str, str], str] = {}


def _available_models(api_key: str) -> list[str]:
    if api_key not in _MODEL_LIST_CACHE:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=10)
        _MODEL_LIST_CACHE[api_key] = [m.id for m in client.models.list(limit=100)]
    return _MODEL_LIST_CACHE[api_key]


def resolve_model(api_key: str, preferred: str) -> str:
    """Return `preferred` if the key can use it, else the newest model of the same family.

    Anthropic retires dated model IDs; a retired ID fails with 404 not_found_error.
    """
    cache_key = (api_key, preferred)
    if cache_key in _RESOLVED_MODEL_CACHE:
        return _RESOLVED_MODEL_CACHE[cache_key]
    try:
        available = _available_models(api_key)
    except Exception:
        return preferred
    if not available or preferred in available:
        resolved = preferred
    else:
        family = next((f for f in ("opus", "sonnet", "haiku") if f in preferred), "")
        same_family = [m for m in available if family and family in m]
        resolved = (same_family or available)[0]
    _RESOLVED_MODEL_CACHE[cache_key] = resolved
    return resolved


def clean_json_response(response_text: str) -> str:
    text = (response_text or "").strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()
    return text.strip()


def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            candidate = re.sub(r",\s*([}\]])", r"\1", match.group(0))
            return json.loads(candidate)
        raise


class LLMClient:
    """Thin wrapper around ChatAnthropic with JSON parse/repair and token accounting."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 6000,
        temperature: float = 0,  # kept for call-site compat; not sent to the API
    ):
        self.api_key = api_key
        model = resolve_model(api_key, model)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature  # unused by API (SDK 2.8+)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._chat = ChatAnthropic(
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            # Do NOT pass temperature — Anthropic Messages API rejects it.
        )

    def _make_chat(self, max_tokens: Optional[int] = None) -> ChatAnthropic:
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        if tokens == self.max_tokens:
            return self._chat
        return ChatAnthropic(
            model=self.model,
            api_key=self.api_key,
            max_tokens=tokens,
        )

    def _record_usage(self, response) -> None:
        usage = getattr(response, "usage_metadata", None) or {}
        if isinstance(usage, dict):
            self.total_input_tokens += int(usage.get("input_tokens", 0) or 0)
            self.total_output_tokens += int(usage.get("output_tokens", 0) or 0)
            return
        self.total_input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.total_output_tokens += int(getattr(usage, "output_tokens", 0) or 0)

    def _content_text(self, response) -> str:
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
                else:
                    parts.append(getattr(block, "text", str(block)))
            return "".join(parts)
        return str(content)

    def _repair_json(self, raw_text: str, max_retries: int = 2) -> Any:
        repair_prompt = (
            "You are a JSON repair tool. Return only valid JSON.\n"
            "If unrepairable, return {}.\n\n"
            f"Text:\n{raw_text}"
        )
        backoff = 1
        chat = self._make_chat(min(self.max_tokens, 1200))
        for attempt in range(max_retries + 1):
            response = chat.invoke([HumanMessage(content=repair_prompt)])
            self._record_usage(response)
            cleaned = clean_json_response(self._content_text(response))
            try:
                return safe_json_loads(cleaned)
            except json.JSONDecodeError:
                if attempt >= max_retries:
                    return {}
                time.sleep(backoff)
                backoff *= 2
        return {}

    async def _arepair_json(self, raw_text: str, max_retries: int = 2) -> Any:
        return await asyncio.to_thread(self._repair_json, raw_text, max_retries)

    def invoke_json(self, prompt: str, max_tokens_override: Optional[int] = None, max_retries: int = 3) -> Any:
        chat = self._make_chat(max_tokens_override)
        backoff = 2
        for attempt in range(max_retries + 1):
            try:
                response = chat.invoke([HumanMessage(content=prompt)])
                self._record_usage(response)
                cleaned = clean_json_response(self._content_text(response))
                try:
                    return safe_json_loads(cleaned)
                except json.JSONDecodeError:
                    return self._repair_json(cleaned)
            except Exception as exc:
                name = type(exc).__name__
                if "RateLimit" not in name and "rate" not in str(exc).lower():
                    if attempt >= max_retries:
                        raise
                if attempt >= max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
        return {}

    async def ainvoke_json(
        self, prompt: str, max_tokens_override: Optional[int] = None, max_retries: int = 3
    ) -> Any:
        chat = self._make_chat(max_tokens_override)
        backoff = 2
        for attempt in range(max_retries + 1):
            try:
                response = await chat.ainvoke([HumanMessage(content=prompt)])
                self._record_usage(response)
                cleaned = clean_json_response(self._content_text(response))
                try:
                    return safe_json_loads(cleaned)
                except json.JSONDecodeError:
                    return await self._arepair_json(cleaned)
            except Exception as exc:
                name = type(exc).__name__
                if "RateLimit" not in name and "rate" not in str(exc).lower():
                    if attempt >= max_retries:
                        raise
                if attempt >= max_retries:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
        return {}


def make_llm(api_key: str, model: str, max_tokens: int = 6000, temperature: float = 0) -> LLMClient:
    return LLMClient(api_key=api_key, model=model, max_tokens=max_tokens, temperature=temperature)
