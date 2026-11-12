"""Legacy Streamlit chatbot — deprecated in v.7."""


def render_chatbot_ui(*_args, **_kwargs):
    raise RuntimeError(
        "Streamlit chatbot is deprecated in Vice Virtue v.7. "
        "Use: uvicorn api_server:app --reload --port 8000 "
        "and npm run dev in userInterface/."
    )
