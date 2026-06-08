"""Strategy Agent — fourth node in the Athena AI workflow.

Generates a ranked set of mitigation strategies.
Uses deterministic mock logic; replace with LLM call in a later phase.
"""

from __future__ import annotations

from app.agents.state import AgentState, StrategyItem


def strategy_agent(state: AgentState) -> AgentState:
    """Produce three candidate mitigation strategies."""
    strategies: list[StrategyItem] = [
        {
            "title": "Reroute affected operation",
            "description": (
                "Redirect impacted workflows to an alternate processing path "
                "to restore normal throughput within 4 hours."
            ),
            "estimated_savings": 85_000.0,
            "effort": "MEDIUM",
            "risk_reduction": 0.65,
            "confidence": 0.82,
        },
        {
            "title": "Notify impacted customers",
            "description": (
                "Send proactive status updates to affected customers to reduce "
                "churn risk and manage service-level expectations."
            ),
            "estimated_savings": 30_000.0,
            "effort": "LOW",
            "risk_reduction": 0.30,
            "confidence": 0.90,
        },
        {
            "title": "Allocate backup resources",
            "description": (
                "Provision additional capacity from the reserve pool to absorb "
                "the operational load while the root cause is addressed."
            ),
            "estimated_savings": 60_000.0,
            "effort": "HIGH",
            "risk_reduction": 0.55,
            "confidence": 0.75,
        },
    ]

    return {**state, "strategies": strategies}
