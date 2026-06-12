"""Decision Engine — fifth node in the Athena AI workflow.

Selects the best strategy using a deterministic scoring function:
    score = estimated_savings + risk_reduction_bonus - effort_penalty

Effort penalties (USD equivalent):
    LOW    → 10 000
    MEDIUM → 25 000
    HIGH   → 50 000

Requires human approval when any of the following is true:
    - Event severity is CRITICAL
    - Decision confidence < 0.75
    - Expected savings > 500 000

This agent is intentionally deterministic (no LLM call) — the decision
engine must be auditable and reproducible. It is `async def` only so it
fits LangGraph's `astream` execution alongside the other async agent nodes.
"""

from __future__ import annotations

from app.agents.state import AgentState, DecisionOutput, StrategyItem

_EFFORT_PENALTY: dict[str, float] = {
    "LOW": 10_000.0,
    "MEDIUM": 25_000.0,
    "HIGH": 50_000.0,
}

# Scale risk_reduction (0–1) to a USD-equivalent bonus so it is comparable
# with estimated_savings on the same numeric axis.
_RISK_REDUCTION_SCALE = 50_000.0


def _score(strategy: StrategyItem) -> float:
    penalty = _EFFORT_PENALTY.get(strategy["effort"], 25_000.0)
    bonus = strategy["risk_reduction"] * _RISK_REDUCTION_SCALE
    return strategy["estimated_savings"] + bonus - penalty


async def decision_agent(state: AgentState) -> AgentState:
    """Select the highest-scoring strategy and emit a decision."""
    strategies = state.get("strategies") or []
    if not strategies:
        # Defensive fallback — should not happen in a correctly wired graph.
        return {
            **state,
            "decision": None,
            "errors": [*state.get("errors", []), "No strategies available for decision engine"],
        }

    best = max(strategies, key=_score)
    event = state["event"]
    severity = str(event.get("severity", "")).upper()
    confidence = best["confidence"]

    expected_savings = best["estimated_savings"]

    requires_approval = (
        severity == "CRITICAL"
        or confidence < 0.75
        or expected_savings > 500_000.0
    )

    decision: DecisionOutput = {
        "selected_action": best,
        "decision_reason": (
            f"Strategy '{best['title']}' selected with score "
            f"{_score(best):,.0f}. "
            f"Estimated savings: ${expected_savings:,.0f}. "
            f"Effort: {best['effort']}."
        ),
        "expected_savings": expected_savings,
        "confidence": confidence,
        "requires_human_approval": requires_approval,
    }

    return {**state, "decision": decision}