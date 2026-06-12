"""Strategy Agent — fourth node in the Athena AI workflow.

Generates a ranked set of mitigation strategies.
Calls Claude (Anthropic) to generate real strategies; falls back to
deterministic mock logic if the API is unavailable.
"""

from __future__ import annotations

import json

from app.agents.llm import call_claude_json
from app.agents.state import AgentState, StrategyItem

_SYSTEM_PROMPT = (
    "You are the Strategy Agent in an operational incident-response pipeline "
    "called Athena AI. Given an event record and the prior agents' "
    "observation, investigation, and prediction, propose exactly THREE "
    "candidate mitigation strategies. Respond with ONLY a single JSON "
    'object — no markdown, no commentary — with exactly one key "strategies" '
    "whose value is an array of exactly 3 objects, each with these keys: "
    '"title" (short string), '
    '"description" (1-2 sentence string explaining the action), '
    '"estimated_savings" (number, estimated USD savings if implemented), '
    '"effort" (string, one of LOW, MEDIUM, HIGH), '
    '"risk_reduction" (number between 0 and 1), '
    '"confidence" (number between 0 and 1).'
)

_FALLBACK_STRATEGIES: list[StrategyItem] = [
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

_VALID_EFFORTS = {"LOW", "MEDIUM", "HIGH"}


async def strategy_agent(state: AgentState) -> AgentState:
    """Produce three candidate mitigation strategies."""
    event = state["event"]
    observation = state.get("observation")
    investigation = state.get("investigation")
    prediction = state.get("prediction")

    fallback = {"strategies": [dict(s) for s in _FALLBACK_STRATEGIES]}

    user_prompt = (
        "Here is the event record (JSON):\n"
        f"{json.dumps(event, default=str, indent=2)}\n\n"
        "Here is the Observer Agent's observation (JSON):\n"
        f"{json.dumps(observation, default=str, indent=2)}\n\n"
        "Here is the Investigation Agent's findings (JSON):\n"
        f"{json.dumps(investigation, default=str, indent=2)}\n\n"
        "Here is the Prediction Agent's risk estimate (JSON):\n"
        f"{json.dumps(prediction, default=str, indent=2)}\n\n"
        "Propose three mitigation strategies and return them as the JSON "
        "object described in the system prompt."
    )

    result = await call_claude_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        fallback=fallback,
    )

    raw_strategies = result.get("strategies")
    if not isinstance(raw_strategies, list) or len(raw_strategies) == 0:
        raw_strategies = fallback["strategies"]

    strategies: list[StrategyItem] = []
    for i, item in enumerate(raw_strategies[:3]):
        if not isinstance(item, dict):
            item = {}
        default = _FALLBACK_STRATEGIES[i % len(_FALLBACK_STRATEGIES)]
        effort = str(item.get("effort", default["effort"])).upper()
        if effort not in _VALID_EFFORTS:
            effort = default["effort"]
        strategies.append(
            {
                "title": str(item.get("title", default["title"])),
                "description": str(item.get("description", default["description"])),
                "estimated_savings": float(
                    item.get("estimated_savings", default["estimated_savings"])
                ),
                "effort": effort,
                "risk_reduction": float(
                    item.get("risk_reduction", default["risk_reduction"])
                ),
                "confidence": float(item.get("confidence", default["confidence"])),
            }
        )

    # Ensure exactly 3 strategies even if the model returned fewer
    while len(strategies) < 3:
        strategies.append(dict(_FALLBACK_STRATEGIES[len(strategies)]))

    return {**state, "strategies": strategies}