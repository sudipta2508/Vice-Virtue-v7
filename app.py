"""PDF report builder + legacy Streamlit entry (deprecated).

Assessment runs via graph/ (LangGraph). Prefer:
  uvicorn api_server:app --reload --port 8000
  cd userInterface && npm run dev
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe_text(value):
    if value is None:
        return ""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf_report(output, catalog, report_label=None, followup_audit=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=0.5 * inch, rightMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=15, textColor=colors.darkblue)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=colors.darkred)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10)
    body = styles["BodyText"]
    mono = ParagraphStyle("Mono", parent=styles["Code"], fontSize=8.7, leading=11)

    flow = []
    flow.append(Paragraph("Leader Character Vice-Virtue Assessment Report", title_style))
    if report_label:
        flow.append(Paragraph(_safe_text(report_label), h3))
    flow.append(Spacer(1, 0.12 * inch))
    flow.append(Paragraph("All evidences are included without filtering.", body))
    flow.append(Spacer(1, 0.12 * inch))

    if followup_audit:
        flow.append(Paragraph("Follow-up Q&A", h2))
        for entry in followup_audit:
            flow.append(
                Paragraph(
                    f"Dimension: {_safe_text(entry.get('dimension', ''))} | "
                    f"Items updated: {_safe_text(entry.get('items_with_new_evidence', []))}",
                    body,
                )
            )
            ans = (entry.get("user_answer") or "")[:2000]
            flow.append(Paragraph(f"Answer excerpt: {_safe_text(ans)}", mono))
        flow.append(Spacer(1, 0.12 * inch))

    for dimension, items in catalog.items():
        flow.append(Paragraph(f"Dimension: {_safe_text(dimension)}", h2))
        flow.append(Spacer(1, 0.08 * inch))
        for item in items:
            key = item["virtue"]
            evidence = output["evidence"][dimension][key]
            analysis = output["analysis"][dimension][key]
            scoring = output["scoring"][dimension][key]
            adjustment = output["adjustment"][dimension][key]
            bh = output["behavioral_hierarchy"][dimension][key]
            co = output["coordinator"][dimension][key]

            flow.append(Paragraph(f"Item: {_safe_text(key)}", h3))
            flow.append(Paragraph(f"Virtue definition: {_safe_text(item.get('item_description', ''))}", body))
            flow.append(
                Paragraph(
                    f"Deficit vice: {_safe_text(item.get('deficit_vice', ''))} - "
                    f"{_safe_text(item.get('deficit_vice_description', ''))}",
                    body,
                )
            )
            flow.append(
                Paragraph(
                    f"Excess vice: {_safe_text(item.get('excess_vice', ''))} - "
                    f"{_safe_text(item.get('excess_vice_definition', ''))}",
                    body,
                )
            )
            flow.append(Spacer(1, 0.06 * inch))

            score_table = Table(
                [
                    ["Stage", "Virtue", "Deficit", "Excess"],
                    [
                        "Raw scoring",
                        str(scoring.get("virtue_score", 0)),
                        str(scoring.get("deficit_vice_score", 0)),
                        str(scoring.get("excess_vice_score", 0)),
                    ],
                    [
                        "Adjusted",
                        str(adjustment.get("virtue_score_adjusted", 0)),
                        str(adjustment.get("deficit_vice_score_adjusted", 0)),
                        str(adjustment.get("excess_vice_score_adjusted", 0)),
                    ],
                    [
                        "Behavioral hierarchy",
                        str(bh.get("virtue_score", 0)),
                        str(bh.get("deficit_vice_score", 0)),
                        str(bh.get("excess_vice_score", 0)),
                    ],
                    [
                        "Final coordinator",
                        str(co.get("final_virtue_score", 0)),
                        str(co.get("final_deficit_vice_score", 0)),
                        str(co.get("final_excess_vice_score", 0)),
                    ],
                ],
                colWidths=[2.2 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch],
            )
            score_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            flow.append(score_table)
            flow.append(Spacer(1, 0.05 * inch))
            flow.append(Paragraph(f"Dominant class: {_safe_text(co.get('dominant_class', 'uncertain'))}", body))
            flow.append(Spacer(1, 0.06 * inch))

            flow.append(Paragraph("Detailed Reasoning", h3))
            flow.append(Paragraph(f"Virtue reasoning: {_safe_text(scoring.get('virtue_reasoning', ''))}", body))
            flow.append(
                Paragraph(f"Deficit vice reasoning: {_safe_text(scoring.get('deficit_vice_reasoning', ''))}", body)
            )
            flow.append(
                Paragraph(f"Excess vice reasoning: {_safe_text(scoring.get('excess_vice_reasoning', ''))}", body)
            )
            flow.append(
                Paragraph(f"Adjustment reasoning: {_safe_text(adjustment.get('adjustment_reasoning', ''))}", body)
            )
            flow.append(
                Paragraph(f"Coordinator reasoning: {_safe_text(co.get('arbitration_reasoning', ''))}", body)
            )
            flow.append(Spacer(1, 0.06 * inch))

            flow.append(Paragraph("Flags", h3))
            for cls in ["virtue", "deficit_vice", "excess_vice"]:
                s = analysis.get(cls, {}).get("special_flags", {})
                flow.append(
                    Paragraph(
                        f"{cls}: situationalInconsistency={s.get('situationalInconsistency', 0)}, "
                        f"socialDesirability={bool((s.get('socialDesirabilityFlags', {}) or {}).get('flag', False))}, "
                        f"negativeBehavior={bool((s.get('negativeBehaviorFlags', {}) or {}).get('flag', False))}",
                        body,
                    )
                )
            flow.append(Spacer(1, 0.06 * inch))

            flow.append(Paragraph("All Evidences (no filtering)", h3))
            for cls in ["virtue", "deficit_vice", "excess_vice"]:
                evs = evidence.get(f"{cls}_evidences", []) or []
                flow.append(Paragraph(f"{cls} evidences ({len(evs)}):", body))
                if not evs:
                    flow.append(Paragraph("- none", mono))
                for ev in evs:
                    flow.append(
                        Paragraph(
                            f"- id={_safe_text(ev.get('evidence_id', ''))} | "
                            f"{_safe_text(ev.get('source_position', ''))} | "
                            f"{_safe_text(ev.get('text', ''))}",
                            mono,
                        )
                    )
                flow.append(Spacer(1, 0.04 * inch))

            flow.append(PageBreak())
    doc.build(flow)
    buffer.seek(0)
    return buffer


def main():
    print(
        "Streamlit UI is deprecated in v.7.\n"
        "Start the API:  uvicorn api_server:app --reload --port 8000\n"
        "Start the UI:   cd userInterface && npm install && npm run dev\n"
    )


if __name__ == "__main__":
    main()
