"""Assessment pipeline entry — delegates to the LangGraph assessment graph."""

from __future__ import annotations

from typing import Callable, Optional

from graph.assessment_graph import run_async_analysis
from graph.defaults import normalize_dimension_result, parse_narrative_to_paragraphs

__all__ = [
    "run_async_analysis",
    "normalize_dimension_result",
    "parse_narrative_to_paragraphs",
]
