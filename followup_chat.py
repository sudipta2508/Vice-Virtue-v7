"""Legacy Streamlit follow-up chat — deprecated in v.7.

Use the React UI + LangGraph session graph instead:
  uvicorn api_server:app --reload --port 8000
"""


def render_followup_chat(*_args, **_kwargs):
    raise RuntimeError(
        "Streamlit follow-up chat is deprecated in Vice Virtue v.7. "
        "Use the React UI with the FastAPI / LangGraph backend."
    )
