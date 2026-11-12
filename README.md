# Vice Virtue v.7 — Leader Character Assessment

LangGraph-based multi-agent assessment with React UI + FastAPI backend.

## Prerequisites

- Python 3.10+ with project dependencies
- Node.js 18+ for the React frontend
- Claude API key (entered in chat at runtime)

## Run

**Terminal 1 — API backend:**

```bash
cd "Vice Virtue v.7"
source ../ivey/bin/activate   # or your venv
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8000
```

**Terminal 2 — React frontend:**

```bash
cd "Vice Virtue v.7/userInterface"
npm install
npm run dev
```

Open http://localhost:5173

Uses the same ports as v.6 (8000 / 5173) — run only one version at a time.

## Architecture

- `api_server.py` — FastAPI REST API
- `graph/` — LangGraph session, assessment, and reassessment graphs
- `followup_logic.py` — Gap detection follow-up helpers
- `userInterface/` — React app (wheel charts + chat with Yes/No/Skip)

## What's new in v.7

- Full LangGraph orchestration (session + 5-stage assessment + reassessment)
- Skip empty-evidence dimensions/items (no wasted LLM calls)
- ChatAnthropic via langchain-anthropic (replaces BaseAgent)
- Targeted follow-up questions naming missing virtue items
- Yes/No/Skip quick-reply buttons in the UI
- Configurable gap threshold; pre-baseline dimensions skipped in follow-up
