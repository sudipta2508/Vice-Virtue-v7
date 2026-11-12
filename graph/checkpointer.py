"""LangGraph checkpointer for session threads."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

_memory_saver: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    global _memory_saver
    if _memory_saver is None:
        _memory_saver = MemorySaver()
    return _memory_saver
