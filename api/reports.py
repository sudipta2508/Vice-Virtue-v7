"""Generate JSON/PDF report downloads for sessions."""

from __future__ import annotations

import json

from fastapi import HTTPException
from fastapi.responses import Response

from app import build_pdf_report
from api.session_store import store


def _report_payload(session: dict, report_type: str):
    if report_type == "baseline":
        output = session.get("out_baseline")
        if not output:
            raise HTTPException(400, "Baseline report not available")
        return (
            output,
            "Baseline — narrative only",
            None,
            "vice_virtue_baseline.json",
            "vice_virtue_baseline.pdf",
        )

    if report_type == "refined":
        followup = session.get("followup_phase")
        has_audit = bool(session.get("followup_audit"))
        output = session.get("out_final")
        if (
            followup != "complete"
            or not has_audit
            or output is None
        ):
            raise HTTPException(400, "Refined report not available")
        audit = session.get("followup_audit")
        return (
            output,
            "Refined — after follow-up",
            audit,
            "vice_virtue_refined.json",
            "vice_virtue_refined.pdf",
        )

    raise HTTPException(400, f"Unknown report type: {report_type}")


def build_json_response(session: dict, report_type: str) -> Response:
    output, _, _, filename, _ = _report_payload(session, report_type)
    body = json.dumps(output, indent=2).encode("utf-8")
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def build_pdf_response(session: dict, report_type: str) -> Response:
    output, label, audit, _, filename = _report_payload(session, report_type)
    pdf_bytes = build_pdf_report(
        output,
        store.catalog,
        report_label=label,
        followup_audit=audit,
    ).getvalue()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def reports_availability(session: dict) -> dict:
    """Which downloads are available for the session."""
    followup = session.get("followup_phase")
    baseline = session.get("out_baseline") is not None
    refined = (
        followup == "complete"
        and bool(session.get("followup_audit"))
        and session.get("out_final") is not None
    )
    return {"baseline": baseline, "refined": refined}
