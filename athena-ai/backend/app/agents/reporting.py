"""Reporting Agent — final node in the Athena AI workflow.

Synthesises all prior agent outputs into executive and technical summaries.
Calls Claude (Anthropic) to write the narrative summaries; falls back to
deterministic mock text if the API is unavailable.

The overall pipeline `confidence_score` is always computed deterministically
(harmonic mean of upstream agent confidences) regardless of LLM availability,
since this value is used for downstream business logic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.agents.llm import call_claude_json
from app.agents.state import AgentState, ReportOutput

_SYSTEM_PROMPT = (
    "You are the Reporting Agent in an operational incident-response "
    "pipeline called Athena AI. Given the full pipeline state — the "
    "original event, the observation, investigation, prediction, candidate "
    "strategies, and the final decision — write the report. Respond with "
    "ONLY a single JSON object — no markdown, no commentary — with exactly "
    "these keys: "
    '"executive_summary" (string, 2-4 sentences for a non-technical '
    "executive audience: what happened, the financial exposure, and the "
    "recommended action), "
    '"technical_summary" (string, 2-4 sentences for an engineering audience: '
    "root cause, impact, strategies considered, and which was selected and "
    'why), '
    '"recommended_action" (string, the title of the recommended action).'
)


async def reporting_agent(state: AgentState) -> AgentState:
    """Produce executive and technical summaries from the full workflow state."""
    event = state["event"]
    decision = state.get("decision")
    prediction = state.get("prediction")
    observation = state.get("observation")
    investigation = state.get("investigation")
    strategies = state.get("strategies")

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
    # This is computed deterministically regardless of LLM availability.
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

    fallback: ReportOutput = {
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

    user_prompt = (
        "Here is the event record (JSON):\n"
        f"{json.dumps(event, default=str, indent=2)}\n\n"
        "Here is the Observer Agent's observation (JSON):\n"
        f"{json.dumps(observation, default=str, indent=2)}\n\n"
        "Here is the Investigation Agent's findings (JSON):\n"
        f"{json.dumps(investigation, default=str, indent=2)}\n\n"
        "Here is the Prediction Agent's risk estimate (JSON):\n"
        f"{json.dumps(prediction, default=str, indent=2)}\n\n"
        "Here are the candidate strategies (JSON):\n"
        f"{json.dumps(strategies, default=str, indent=2)}\n\n"
        "Here is the Decision Engine's selected action (JSON):\n"
        f"{json.dumps(decision, default=str, indent=2)}\n\n"
        "Write the report as the JSON object described in the system prompt."
    )

    result = await call_claude_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        fallback={
            "executive_summary": fallback["executive_summary"],
            "technical_summary": fallback["technical_summary"],
            "recommended_action": fallback["recommended_action"],
        },
    )

    report: ReportOutput = {
        "executive_summary": str(
            result.get("executive_summary", fallback["executive_summary"])
        ),
        "technical_summary": str(
            result.get("technical_summary", fallback["technical_summary"])
        ),
        "recommended_action": str(
            result.get("recommended_action", fallback["recommended_action"])
        ),
        # These two are always computed deterministically, never from the LLM.
        "estimated_savings": expected_savings,
        "confidence": overall_confidence,
    }

    return {
        **state,
        "report": report,
        "confidence_score": overall_confidence,
        "completed_at": datetime.now(UTC),
    }