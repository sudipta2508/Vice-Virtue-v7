"""Legacy agent package — assessment now runs via graph/ (LangGraph + ChatAnthropic).

Kept for Streamlit legacy imports (app.py / chatbot.py). Prefer graph.* for new code.
"""

from graph.defaults import parse_narrative_to_paragraphs

__all__ = ["parse_narrative_to_paragraphs"]
