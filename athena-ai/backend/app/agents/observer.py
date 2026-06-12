"""Observer Agent — first node in the Athena AI workflow.

Analyses the raw event and produces a structured observation.
Calls Claude (Anthropic) to generate a real assessment; falls back to
deterministic mock logic if the API is unavailable.
"""

from __future__ import annotations

import json

from app.agents.llm import call_claude_json
from app.agents.state import AgentState, ObservationOutput

_SYSTEM_PROMPT = (
    "You are the Observer Agent in an operational incident-response pipeline "
    "called Athena AI. Given a raw event record, produce a structured "
    "observation. Respond with ONLY a single JSON object — no markdown, no "
    "commentary — with exactly these keys: "
    '"summary" (string, 1-2 sentences describing what happened), '
    '"detected_type" (string, the type of issue you detect), '
    '"priority" (string, one of LOW, MEDIUM, HIGH, CRITICAL), '
    '"risk_indicators" (array of short strings naming specific risk signals), '
    '"confidence" (number between 0 and 1).'
)


async def observer_agent(state: AgentState) -> AgentState:
    """Produce an observation from the event snapshot."""
    event = state["event"]

    fallback: ObservationOutput = {
        "summary": "Operational event detected",
        "detected_type": str(event.get("event_type", "unknown")),
        "priority": str(event.get("severity", "MEDIUM")),
        "risk_indicators": [],
        "confidence": 0.85,
    }

    user_prompt = (
        "Here is the event record (JSON):\n"
        f"{json.dumps(event, default=str, indent=2)}\n\n"
        "Analyse this event and return your observation as the JSON object "
        "described in the system prompt."
    )

    result = await call_claude_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        fallback=dict(fallback),
    )

    observation: ObservationOutput = {
        "summary": str(result.get("summary", fallback["summary"])),
        "detected_type": str(result.get("detected_type", fallback["detected_type"])),
        "priority": str(result.get("priority", fallback["priority"])),
        "risk_indicators": list(result.get("risk_indicators") or []),
        "confidence": float(result.get("confidence", fallback["confidence"])),
    }

    return {**state, "observation": observation}