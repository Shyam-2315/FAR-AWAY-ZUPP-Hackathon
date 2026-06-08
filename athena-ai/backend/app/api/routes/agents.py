"""Agent workflow routes.

POST /api/agents/run/{event_id}
    Trigger the full multi-agent LangGraph pipeline for a given event.
    Requires ANALYST role or above.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AnalystOrAbove
from app.db.session import get_db_session
from app.schemas.agents import WorkflowResponse
from app.services.agent_workflow_service import AgentWorkflowService, WorkflowError
from app.services.event_service import EventNotFoundError

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/run/{event_id}",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the multi-agent workflow for an event",
    description=(
        "Triggers the full Observer → Investigation → Prediction → Strategy → "
        "Decision → Reporting pipeline for the specified event. "
        "The event status is updated to PROCESSING while the workflow runs and "
        "RESOLVED on success (FAILED on error). "
        "Requires ANALYST role or above."
    ),
)
async def run_workflow(
    event_id: uuid.UUID,
    current_user: AnalystOrAbove,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkflowResponse:
    svc = AgentWorkflowService(session)

    try:
        final_state = await svc.run(event_id, current_user)
    except EventNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVENT_NOT_FOUND", "message": str(exc)},
        ) from exc
    except WorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "WORKFLOW_FAILED", "message": str(exc)},
        ) from exc

    # All agents must have produced output for a successful run.
    # Guard against a partially-complete state (defensive).
    missing = [
        field
        for field in ("observation", "investigation", "prediction",
                      "strategies", "decision", "report")
        if not final_state.get(field)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "WORKFLOW_INCOMPLETE",
                "message": f"Workflow completed but outputs missing: {missing}",
            },
        )

    return WorkflowResponse(
        event_id=final_state["event_id"],
        event_status="RESOLVED",
        observation=final_state["observation"],  # type: ignore[arg-type]
        investigation=final_state["investigation"],  # type: ignore[arg-type]
        prediction=final_state["prediction"],  # type: ignore[arg-type]
        strategies=final_state["strategies"],  # type: ignore[arg-type]
        decision=final_state["decision"],  # type: ignore[arg-type]
        report=final_state["report"],  # type: ignore[arg-type]
        confidence_score=final_state["confidence_score"],
        started_at=final_state["started_at"],
        completed_at=final_state["completed_at"],  # type: ignore[arg-type]
        errors=final_state["errors"],
    )
