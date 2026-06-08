"""Pydantic response schemas for the agent workflow endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ObservationSchema(BaseModel):
    summary: str
    detected_type: str
    priority: str
    risk_indicators: list[str]
    confidence: float


class InvestigationSchema(BaseModel):
    root_cause: str
    impact: str
    evidence: list[str]
    confidence: float


class PredictionSchema(BaseModel):
    revenue_risk: float
    delay_probability: float
    churn_probability: float
    severity_score: float
    confidence: float


class StrategyItemSchema(BaseModel):
    title: str
    description: str
    estimated_savings: float
    effort: str
    risk_reduction: float
    confidence: float


class DecisionSchema(BaseModel):
    selected_action: StrategyItemSchema
    decision_reason: str
    expected_savings: float
    confidence: float
    requires_human_approval: bool


class ReportSchema(BaseModel):
    executive_summary: str
    technical_summary: str
    recommended_action: str
    estimated_savings: float
    confidence: float


class WorkflowResponse(BaseModel):
    """Complete workflow result returned to the frontend."""

    event_id: uuid.UUID
    event_status: str
    observation: ObservationSchema
    investigation: InvestigationSchema
    prediction: PredictionSchema
    strategies: list[StrategyItemSchema]
    decision: DecisionSchema
    report: ReportSchema
    confidence_score: float
    started_at: datetime
    completed_at: datetime
    errors: list[str]


class WorkflowErrorResponse(BaseModel):
    """Clean error envelope returned when the workflow fails."""

    event_id: uuid.UUID
    event_status: str
    error: str
    errors: list[str]
