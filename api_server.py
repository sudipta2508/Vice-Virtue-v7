"""FastAPI server for React frontend."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.orchestrator import handle_message
from api.reports import (
    build_json_response,
    build_pdf_response,
    reports_availability,
)
from api.schemas import MessageRequest, SessionResponse
from api.session_store import store
from api.ui_transform import (
    build_catalog_response,
    build_dimension_chart_data,
    build_dimension_items,
)

app = FastAPI(title="Leader Character Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/catalog")
def get_catalog():
    return build_catalog_response(store.catalog)


@app.post("/api/sessions", response_model=SessionResponse)
def create_session():
    session = store.create()
    return store.public_view(session)


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return store.public_view(session)


@app.post("/api/sessions/{session_id}/messages", response_model=SessionResponse)
async def post_message(session_id: str, body: MessageRequest):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return await handle_message(session_id, body.content)


@app.get("/api/sessions/{session_id}/results")
def get_results(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    baseline_out = session.get("out_baseline")
    if not baseline_out:
        raise HTTPException(400, "Baseline results not ready")

    catalog = store.catalog
    baseline_chart = build_dimension_chart_data(baseline_out, catalog)

    followup = session.get("followup_phase")
    has_refined = (
        followup == "complete"
        and bool(session.get("followup_audit"))
        and session.get("out_final") is not None
    )

    if has_refined:
        refined_out = session.get("out_final")
        refined_chart = build_dimension_chart_data(refined_out, catalog)
        return {
            "mode": "dual",
            "baseline": baseline_chart,
            "refined": refined_chart,
        }

    return {
        "mode": "single",
        "baseline": baseline_chart,
        "refined": None,
    }


@app.get("/api/sessions/{session_id}/reports/availability")
def get_reports_availability(session_id: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return reports_availability(session)


@app.get("/api/sessions/{session_id}/reports/{report_type}/json")
def download_report_json(session_id: str, report_type: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if report_type not in ("baseline", "refined"):
        raise HTTPException(400, "report_type must be baseline or refined")
    return build_json_response(session, report_type)


@app.get("/api/sessions/{session_id}/reports/{report_type}/pdf")
def download_report_pdf(session_id: str, report_type: str):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if report_type not in ("baseline", "refined"):
        raise HTTPException(400, "report_type must be baseline or refined")
    return build_pdf_response(session, report_type)


@app.get("/api/sessions/{session_id}/dimensions/{dimension_name}/items")
def get_dimension_items(session_id: str, dimension_name: str, source: str = "refined"):
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    catalog = store.catalog
    if dimension_name not in catalog:
        raise HTTPException(404, f"Dimension '{dimension_name}' not found")

    if source == "baseline":
        output = session.get("out_baseline")
    else:
        output = session.get("out_final") or session.get("out_working") or session.get("out_baseline")

    if not output:
        raise HTTPException(400, "Results not ready")

    return {
        "dimension": dimension_name,
        "source": source,
        "items": build_dimension_items(output, catalog, dimension_name),
    }
