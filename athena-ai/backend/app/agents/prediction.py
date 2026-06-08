"""Prediction Agent — third node in the Athena AI workflow.

Generates financial and operational risk predictions.
Uses deterministic mock logic; replace with LLM call in a later phase.
"""

from __future__ import annotations

from app.agents.state import AgentState, PredictionOutput


def prediction_agent(state: AgentState) -> AgentState:
    """Produce risk predictions from the investigation output."""
    prediction: PredictionOutput = {
        "revenue_risk": 125_000.0,
        "delay_probability": 0.72,
        "churn_probability": 0.18,
        "severity_score": 7.5,
        "confidence": 0.78,
    }

    return {**state, "prediction": prediction}
