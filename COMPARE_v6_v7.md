# Side-by-side comparison: v.6 vs v.7

v.7 keeps the same API contract and result shape as v.6 so you can compare scores on one narrative.

## Prerequisites

- Your Claude API key
- Only one version running at a time (both use ports 8000 / 5173)

## Sample narrative

Use any narrative you already trust from v.6 (or a short CEO/leader story of ~300+ words covering several LCIA dimensions).

## Run v.6

```bash
cd "Vice Virtue v.6"
source ../ivey/bin/activate
uvicorn api_server:app --reload --port 8000
```

```bash
cd userInterface   # repo-root UI
npm run dev
```

1. Open http://localhost:5173
2. Paste API key → narrative → decline or complete follow-up
3. Download **baseline** JSON (`vice_virtue_baseline.json`)
4. Note dimension means / dominant classes of interest

Stop both processes.

## Run v.7

```bash
cd "Vice Virtue v.7"
source ../ivey/bin/activate
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8000
```

```bash
cd "Vice Virtue v.7/userInterface"
npm install
npm run dev
```

1. Open http://localhost:5173
2. Same API key and **the same narrative**
3. Download baseline JSON
4. Compare coordinator scores per item / dimension means

## What should match vs differ

| Area | Expectation |
|------|-------------|
| Catalog / dimensions | Same |
| Result keys (`evidence`, `scoring`, `coordinator`, …) | Same |
| Empty-evidence items | v.7 should be **0 / uncertain**, not 3 |
| Sparse dimensions | v.7 skips LLM stages 2–5 → faster, fewer tokens |
| Follow-up questions | v.7 names missing virtue items |
| UI | v.7 shows Yes/No/Skip + arbitration block |

## Automated checks already run in v.7

```bash
cd "Vice Virtue v.7"
python -m pytest tests/ -q
```

These cover post-process zeros, gap detection, empty-dimension skip, and quick-reply phases — without calling Claude.
