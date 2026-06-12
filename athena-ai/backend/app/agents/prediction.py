"""Prediction Agent — third node in the Athena AI workflow.

Generates financial and operational risk predictions.
Calls Claude (Anthropic) to generate a real prediction; falls back to
deterministic mock logic if the API is unavailable.
"""

from __future__ import annotations

import json

from app.agents.llm import call_claude_json
from app.agents.state import AgentState, PredictionOutput

_SYSTEM_PROMPT = (
    "You are the Prediction Agent in an operational incident-response "
    "pipeline called Athena AI. Given an event record and the prior agents' "
    "observation and investigation, estimate the financial and operational "
    "risk. Respond with ONLY a single JSON object — no markdown, no "
    "commentary — with exactly these keys: "
    '"revenue_risk" (number, estimated USD revenue at risk), '
    '"delay_probability" (number between 0 and 1), '
    '"churn_probability" (number between 0 and 1), '
    '"severity_score" (number between 0 and 10), '
    '"confidence" (number between 0 and 1). '
    "Base your estimates on realistic operational reasoning given the event "
    "details provided."
)


async def prediction_agent(state: AgentState) -> AgentState:
    """Produce risk predictions from the investigation output."""
    event = state["event"]
    observation = state.get("observation")
    investigation = state.get("investigation")

    fallback: PredictionOutput = {
        "revenue_risk": 125_000.0,
        "delay_probability": 0.72,
        "churn_probability": 0.18,
        "severity_score": 7.5,
        "confidence": 0.78,
    }

    user_prompt = (
        "Here is the event record (JSON):\n"
        f"{json.dumps(event, default=str, indent=2)}\n\n"
        "Here is the Observer Agent's observation (JSON):\n"
        f"{json.dumps(observation, default=str, indent=2)}\n\n"
        "Here is the Investigation Agent's findings (JSON):\n"
        f"{json.dumps(investigation, default=str, indent=2)}\n\n"
        "Estimate the risk and return your prediction as the JSON object "
        "described in the system prompt."
    )

    result = await call_claude_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        fallback=dict(fallback),
    )

    prediction: PredictionOutput = {
        "revenue_risk": float(result.get("revenue_risk", fallback["revenue_risk"])),
        "delay_probability": float(
            result.get("delay_probability", fallback["delay_probability"])
        ),
        "churn_probability": float(
            result.get("churn_probability", fallback["churn_probability"])
        ),
        "severity_score": float(result.get("severity_score", fallback["severity_score"])),
        "confidence": float(result.get("confidence", fallback["confidence"])),
    }

    return {**state, "prediction": prediction}