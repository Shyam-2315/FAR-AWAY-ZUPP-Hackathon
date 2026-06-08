"""Reporting Agent — final node in the Athena AI workflow.

Synthesises all prior agent outputs into executive and technical summaries.
Also computes the overall pipeline confidence_score.
Uses deterministic mock logic; replace with LLM call in a later phase.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.agents.state import AgentState, ReportOutput


def reporting_agent(state: AgentState) -> AgentState:
    """Produce executive and technical summaries from the full workflow state."""
    event = state["event"]
    decision = state.get("decision")
    prediction = state.get("prediction")
    observation = state.get("observation")

    title = str(event.get("title", "event"))
    severity = str(event.get("severity", "UNKNOWN"))
    event_type = str(event.get("event_type", "unknown"))

    selected_title = (
        decision["selected_action"]["title"] if decision else "no action selected"
    )
    expected_savings = decision["expected_savings"] if decision else 0.0
    requires_approval = decision["requires_human_approval"] if decision else False
    approval_note = " Human approval required before execution." if requires_approval else ""

    revenue_risk = prediction["revenue_risk"] if prediction else 0.0
    obs_summary = observation["summary"] if observation else "No observation available."

    # Overall confidence is the harmonic mean of all agent confidences that
    # produced output — gives a conservative estimate of pipeline reliability.
    confidences: list[float] = []
    if observation:
        confidences.append(observation["confidence"])
    if state.get("investigation"):
        confidences.append(state["investigation"]["confidence"])  # type: ignore[index]
    if prediction:
        confidences.append(prediction["confidence"])
    if decision:
        confidences.append(decision["confidence"])

    overall_confidence = (
        len(confidences) / sum(1.0 / c for c in confidences if c > 0)
        if confidences
        else 0.0
    )

    report: ReportOutput = {
        "executive_summary": (
            f"A {severity} severity {event_type} event '{title}' was detected and analysed. "
            f"{obs_summary} "
            f"Estimated financial exposure: ${revenue_risk:,.0f}. "
            f"Recommended action: {selected_title}.{approval_note}"
        ),
        "technical_summary": (
            f"Workflow completed for event '{title}' (type={event_type}, severity={severity}). "
            f"Root cause and impact assessed. "
            f"Three mitigation strategies generated; "
            f"'{selected_title}' selected by decision engine. "
            f"Overall pipeline confidence: {overall_confidence:.2f}."
        ),
        "recommended_action": selected_title,
        "estimated_savings": expected_savings,
        "confidence": overall_confidence,
    }

    return {
        **state,
        "report": report,
        "confidence_score": overall_confidence,
        "completed_at": datetime.now(UTC),
    }
