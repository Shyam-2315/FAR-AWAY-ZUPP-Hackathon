"""Investigation Agent — second node in the Athena AI workflow.

Performs root-cause analysis based on the observation.
Uses deterministic mock logic; replace with LLM call in a later phase.
"""

from __future__ import annotations

from app.agents.state import AgentState, InvestigationOutput


def investigation_agent(state: AgentState) -> AgentState:
    """Produce a root-cause investigation from the observation."""
    investigation: InvestigationOutput = {
        "root_cause": "Initial root cause analysis generated from event context",
        "impact": "Potential operational delay and customer impact",
        "evidence": [],
        "confidence": 0.80,
    }

    return {**state, "investigation": investigation}
