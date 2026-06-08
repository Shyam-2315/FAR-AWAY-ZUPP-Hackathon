"""AgentState — the shared mutable state object threaded through the LangGraph workflow.

All fields are typed explicitly so the graph can be validated at build time and
so the final JSON output is deterministic and frontend-safe.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TypedDict


class ObservationOutput(TypedDict):
    summary: str
    detected_type: str
    priority: str
    risk_indicators: list[str]
    confidence: float


class InvestigationOutput(TypedDict):
    root_cause: str
    impact: str
    evidence: list[str]
    confidence: float


class PredictionOutput(TypedDict):
    revenue_risk: float
    delay_probability: float
    churn_probability: float
    severity_score: float
    confidence: float


class StrategyItem(TypedDict):
    title: str
    description: str
    estimated_savings: float
    effort: str          # LOW | MEDIUM | HIGH
    risk_reduction: float
    confidence: float


class DecisionOutput(TypedDict):
    selected_action: StrategyItem
    decision_reason: str
    expected_savings: float
    confidence: float
    requires_human_approval: bool


class ReportOutput(TypedDict):
    executive_summary: str
    technical_summary: str
    recommended_action: str
    estimated_savings: float
    confidence: float


class AgentState(TypedDict):
    """Mutable workflow state passed through every LangGraph node."""

    # Input
    event_id: uuid.UUID
    event: dict[str, Any]          # serialised event snapshot

    # Agent outputs (None until that node runs)
    observation: ObservationOutput | None
    investigation: InvestigationOutput | None
    prediction: PredictionOutput | None
    strategies: list[StrategyItem] | None
    decision: DecisionOutput | None
    report: ReportOutput | None

    # Runtime metadata
    errors: list[str]
    confidence_score: float        # overall pipeline confidence (set by reporting agent)
    started_at: datetime
    completed_at: datetime | None
