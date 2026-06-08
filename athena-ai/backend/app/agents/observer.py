"""Observer Agent — first node in the Athena AI workflow.

Analyses the raw event and produces a structured observation.
Uses deterministic mock logic; replace with LLM call in a later phase.
"""

from __future__ import annotations

from app.agents.state import AgentState, ObservationOutput


def observer_agent(state: AgentState) -> AgentState:
    """Produce an observation from the event snapshot."""
    event = state["event"]

    observation: ObservationOutput = {
        "summary": "Operational event detected",
        "detected_type": str(event.get("event_type", "unknown")),
        "priority": str(event.get("severity", "MEDIUM")),
        "risk_indicators": [],
        "confidence": 0.85,
    }

    return {**state, "observation": observation}
