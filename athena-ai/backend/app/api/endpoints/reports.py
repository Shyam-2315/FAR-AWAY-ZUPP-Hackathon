"""Report download routes.

GET /api/reports/{event_id}/pdf
    Generate and stream a structured PDF report for a completed event.
    Fetches the event, its latest Report record (executive/technical
    summaries + financials), and its latest WorkflowRun record (raw agent
    pipeline outputs) from PostgreSQL, then formats everything into a
    downloadable PDF using ReportLab.  Requires VIEWER role or above.
"""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_role
from app.db.session import get_db_session
from app.models.enums import UserRole
from app.models.user import User
from app.models.workflow_run import WorkflowRun
from app.services.event_service import EventService, EventServiceError

router = APIRouter(prefix="/reports", tags=["reports"])


# ------------------------------------------------------------------ #
# Formatting helpers for raw JSONB pipeline output
# ------------------------------------------------------------------ #


def _format_pipeline_value(value: Any) -> str | None:
    """Render a JSONB agent-output value (dict / list / scalar) as readable text.

    - dict: one "Label: value" line per key, title-cased keys, newline-joined
    - list of dicts (e.g. strategies): each item rendered as a small block,
      separated by blank lines
    - list of scalars: comma-separated
    - scalar: str()
    - None / empty: returns None so the caller can show the "no output" message
    """
    if value is None:
        return None

    if isinstance(value, dict):
        if not value:
            return None
        lines = []
        for key, val in value.items():
            label = key.replace("_", " ").title()
            if isinstance(val, list):
                if val and isinstance(val[0], dict):
                    # nested list of dicts (e.g. decision.selected_action) —
                    # render recursively, indented
                    nested = _format_pipeline_value(val)
                    lines.append(f"{label}:<br/>{nested}")
                else:
                    lines.append(f"{label}: {', '.join(str(v) for v in val) or '—'}")
            elif isinstance(val, dict):
                nested = _format_pipeline_value(val)
                lines.append(f"{label}:<br/>{nested}")
            elif isinstance(val, float):
                lines.append(f"{label}: {val:,.3f}")
            else:
                lines.append(f"{label}: {val}")
        return "<br/>".join(lines)

    if isinstance(value, list):
        if not value:
            return None
        if isinstance(value[0], dict):
            blocks = []
            for i, item in enumerate(value, start=1):
                inner = _format_pipeline_value(item)
                blocks.append(f"<b>Option {i}</b><br/>{inner}")
            return "<br/><br/>".join(blocks)
        return ", ".join(str(v) for v in value)

    return str(value)


# ------------------------------------------------------------------ #
# PDF builder
# ------------------------------------------------------------------ #


def _build_pdf(event_data: dict) -> bytes:  # type: ignore[type-arg]
    """Render all agent outputs for one event into a PDF byte stream.

    Layout sections:
        1. Header bar  — Athena AI branding + generation timestamp
        2. Event meta  — title, type, severity, status, tenant, created_at
        3. Executive Summary  — from the Report record
        4. Technical Summary  — from the Report record
        5. Financial Impact   — estimated_savings + confidence
        6. Agent Pipeline     — observation → investigation → prediction →
                                strategies → decision (from WorkflowRun)
        7. Footer             — event ID for traceability
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Athena AI Report — {event_data.get('title', 'Event')}",
        author="Athena AI",
    )

    base_styles = getSampleStyleSheet()

    style_h1 = ParagraphStyle(
        "AthenaH1",
        parent=base_styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
        spaceBefore=0,
    )
    style_h2 = ParagraphStyle(
        "AthenaH2",
        parent=base_styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#334155"),
        spaceBefore=14,
        spaceAfter=4,
    )
    style_body = ParagraphStyle(
        "AthenaBody",
        parent=base_styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
    )
    style_caption = ParagraphStyle(
        "AthenaCaption",
        parent=base_styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
    )

    story = []

    # ------------------------------------------------------------------ #
    # 1. Header
    # ------------------------------------------------------------------ #
    story.append(Paragraph("Athena AI — Executive Intelligence Report", style_h1))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            style_caption,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------ #
    # 2. Event metadata table
    # ------------------------------------------------------------------ #
    story.append(Paragraph("Event Details", style_h2))

    meta_rows = [
        ["Title", event_data.get("title", "—")],
        ["Event Type", event_data.get("event_type", "—")],
        ["Severity", event_data.get("severity", "—")],
        ["Status", event_data.get("status", "—")],
        ["Tenant", event_data.get("tenant_id") or "—"],
        ["Created", str(event_data.get("created_at", "—"))],
        ["Event ID", str(event_data.get("id", "—"))],
    ]

    meta_table = Table(
        meta_rows,
        colWidths=[40 * mm, 130 * mm],
        hAlign="LEFT",
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------ #
    # Helper: render a named section with a grey heading and body text.
    # ------------------------------------------------------------------ #
    def _section(heading: str, content: str | None) -> None:
        story.append(Paragraph(heading, style_h2))
        story.append(
            Paragraph(
                content or "No output recorded for this stage.",
                style_body,
            )
        )
        story.append(Spacer(1, 4 * mm))

    # ------------------------------------------------------------------ #
    # 3 & 4.  Report summaries (from the Report ORM record)
    # ------------------------------------------------------------------ #
    report = event_data.get("report") or {}

    _section("Executive Summary", report.get("executive_summary"))
    _section("Technical Summary", report.get("technical_summary"))

    # ------------------------------------------------------------------ #
    # 5. Financial impact
    # ------------------------------------------------------------------ #
    story.append(Paragraph("Financial Impact", style_h2))

    savings_raw = report.get("estimated_savings")
    confidence_raw = report.get("confidence")

    savings_str = (
        f"${float(savings_raw):,.2f}" if savings_raw is not None else "Not calculated"
    )
    confidence_str = (
        f"{float(confidence_raw) * 100:.1f}%" if confidence_raw is not None else "N/A"
    )

    fin_rows = [
        ["Estimated Savings", savings_str],
        ["Confidence Score", confidence_str],
    ]
    fin_table = Table(fin_rows, colWidths=[60 * mm, 110 * mm], hAlign="LEFT")
    fin_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(fin_table)
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------ #
    # 6. Agent pipeline outputs (from the WorkflowRun record)
    # ------------------------------------------------------------------ #
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Paragraph("Agent Pipeline Outputs", style_h2))

    pipeline = event_data.get("pipeline") or {}
    _section("Observer — Observation", _format_pipeline_value(pipeline.get("observation")))
    _section(
        "Investigator — Root Cause Analysis",
        _format_pipeline_value(pipeline.get("investigation")),
    )
    _section("Predictor — Financial Exposure", _format_pipeline_value(pipeline.get("prediction")))
    _section("Strategy Agent — Options", _format_pipeline_value(pipeline.get("strategies")))
    _section("Decision Engine — Chosen Action", _format_pipeline_value(pipeline.get("decision")))

    # ------------------------------------------------------------------ #
    # 7. Footer
    # ------------------------------------------------------------------ #
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            f"Athena AI Autonomous Intelligence Platform · Report ID: {event_data.get('id', '—')}",
            style_caption,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ------------------------------------------------------------------ #
# Route
# ------------------------------------------------------------------ #


@router.get(
    "/{event_id}/pdf",
    summary="Download a structured PDF report for a completed event",
    description=(
        "Fetches the event, its latest Report record (summaries + "
        "financials), and its latest WorkflowRun record (raw agent pipeline "
        "outputs) from PostgreSQL, then streams a formatted PDF file as a "
        "downloadable attachment. Requires VIEWER role or above."
    ),
    response_class=StreamingResponse,
)
async def download_report_pdf(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_min_role(UserRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StreamingResponse:
    _ = current_user

    # ------------------------------------------------------------------ #
    # Fetch event from PostgreSQL via the existing EventService so we
    # reuse all the same not-found / soft-delete handling already in place.
    # ------------------------------------------------------------------ #
    event_svc = EventService(session)
    try:
        event = await event_svc.get_event(event_id)
    except EventServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVENT_NOT_FOUND", "message": str(exc)},
        ) from exc

    # ------------------------------------------------------------------ #
    # Collect the most recent Report record attached to this event.
    # The Event model has a `reports` relationship (lazy="selectin") so
    # the list is already loaded — no extra query needed.
    # ------------------------------------------------------------------ #
    latest_report = None
    if event.reports:
        latest_report = sorted(
            event.reports,
            key=lambda r: r.created_at,
            reverse=True,
        )[0]

    report_dict: dict = {}  # type: ignore[type-arg]
    if latest_report is not None:
        report_dict = {
            "executive_summary": getattr(latest_report, "executive_summary", None),
            "technical_summary": getattr(latest_report, "technical_summary", None),
            "estimated_savings": getattr(latest_report, "estimated_savings", None),
            "confidence": getattr(latest_report, "confidence", None),
        }

    # ------------------------------------------------------------------ #
    # Collect the most recent WorkflowRun record for this event — this is
    # where the raw per-agent JSONB outputs (observation, investigation,
    # prediction, strategies, decision) actually live.
    # ------------------------------------------------------------------ #
    pipeline_dict: dict = {}  # type: ignore[type-arg]

    run_result = await session.execute(
        select(WorkflowRun)
        .where(WorkflowRun.event_id == event_id)
        .order_by(WorkflowRun.completed_at.desc())
        .limit(1)
    )
    latest_run = run_result.scalar_one_or_none()

    if latest_run is not None:
        pipeline_dict = {
            "observation": getattr(latest_run, "observation", None),
            "investigation": getattr(latest_run, "investigation", None),
            "prediction": getattr(latest_run, "prediction", None),
            "strategies": getattr(latest_run, "strategies", None),
            "decision": getattr(latest_run, "decision", None),
        }

    event_payload = {
        "id": str(event.id),
        "title": event.title,
        "event_type": event.event_type,
        "severity": event.severity.value if hasattr(event.severity, "value") else str(event.severity),
        "status": event.status.value if hasattr(event.status, "value") else str(event.status),
        "tenant_id": event.tenant_id,
        "created_at": event.created_at.strftime("%Y-%m-%d %H:%M UTC")
        if hasattr(event, "created_at") and event.created_at
        else "—",
        "report": report_dict,
        "pipeline": pipeline_dict,
    }

    # ------------------------------------------------------------------ #
    # Build the PDF bytes synchronously (ReportLab is CPU-bound but fast
    # for single-event documents — typically < 50 ms).
    # ------------------------------------------------------------------ #
    pdf_bytes = _build_pdf(event_payload)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in event.title)[:60]
    filename = f"athena-report-{safe_title}-{event_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )