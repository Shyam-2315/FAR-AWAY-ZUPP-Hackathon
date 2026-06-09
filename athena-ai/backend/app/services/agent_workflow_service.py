"""Agent workflow service — orchestrates the LangGraph pipeline for a given event.

Responsibilities:
  1. Fetch and validate the event (404 if missing/soft-deleted).
  2. Transition event status -> IN_PROGRESS and record WORKFLOW_STARTED activity.
  3. Serialise the event into a plain dict suitable for the AgentState.
  4. Invoke the compiled LangGraph workflow synchronously (all agents are sync).
  5. On success  → RESOLVED + WORKFLOW_COMPLETED activity.
  6. On failure  → FAILED   + WORKFLOW_FAILED  activity.
  7. Return the final AgentState for the route to render.

Persistence of investigation, prediction, recommendations, decision, and report
rows is intentionally deferred to Phase 3.2.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.models.enums import EventActivityType
from app.models.user import User
from app.orchestrator.workflow import get_workflow
from app.services.event_service import EventService


class WorkflowError(Exception):
    """Raised when the workflow pipeline itself encounters an unrecoverable error."""

    def __init__(self, message: str, *, event_id: uuid.UUID) -> None:
        super().__init__(message)
        self.event_id = event_id


def _serialise_event(event: object) -> dict[str, Any]:
    """Convert an ORM Event to a plain JSON-safe dict for AgentState."""
    from app.models.event import Event as EventModel

    e = cast(EventModel, event)
    return {
        "id": str(e.id),
        "title": e.title,
        "description": e.description,
        "event_type": e.event_type,
        "severity": e.severity.value,
        "status": e.status.value,
        "source": e.source,
        "tenant_id": e.tenant_id,
        "metadata": e.event_metadata,
        "created_by": str(e.created_by),
    }


class AgentWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._event_svc = EventService(session)

    async def run(self, event_id: uuid.UUID, actor: User) -> AgentState:
        """Run the full multi-agent pipeline for the given event.

        Returns the final AgentState on success.
        Raises EventNotFoundError (→ 404) if the event does not exist.
        Raises WorkflowError (→ 500) if the pipeline fails after starting.
        """
        # ── 1. Fetch event (raises 404 if not found / soft-deleted) ──────
        event = await self._event_svc.get_event(event_id)

        # 2. Mark IN_PROGRESS + record WORKFLOW_STARTED.
        await self._event_svc.record_workflow_activity(
            event_id,
            EventActivityType.WORKFLOW_STARTED,
            actor_id=actor.id,
            details={"triggered_by": str(actor.id)},
        )

        started_at = datetime.now(UTC)

        # ── 3. Build initial state ─────────────────────────────────────────
        initial_state: AgentState = {
            "event_id": event_id,
            "event": _serialise_event(event),
            "observation": None,
            "investigation": None,
            "prediction": None,
            "strategies": None,
            "decision": None,
            "report": None,
            "errors": [],
            "confidence_score": 0.0,
            "started_at": started_at,
            "completed_at": None,
        }

        # ── 4. Run LangGraph workflow ──────────────────────────────────────
        try:
            workflow = get_workflow()
            # LangGraph compiled graphs expose .invoke() for synchronous execution.
            # The return type is intentionally untyped in LangGraph's stubs.
            final_state: AgentState = workflow.invoke(initial_state)  # type: ignore[attr-defined]
        except Exception as exc:
            # ── 5a. Failure path ──────────────────────────────────────────
            error_msg = str(exc)
            await self._event_svc.record_workflow_activity(
                event_id,
                EventActivityType.WORKFLOW_FAILED,
                actor_id=actor.id,
                details={"error": error_msg},
            )
            raise WorkflowError(error_msg, event_id=event_id) from exc

        # ── 5b. Success path ───────────────────────────────────────────────
        decision_out = final_state.get("decision")
        requires_approval: bool = False
        if isinstance(decision_out, dict):
            requires_approval = bool(decision_out.get("requires_human_approval", False))

        await self._event_svc.record_workflow_activity(
            event_id,
            EventActivityType.WORKFLOW_COMPLETED,
            actor_id=actor.id,
            details={
                "confidence_score": final_state.get("confidence_score", 0.0),
                "requires_human_approval": requires_approval,
            },
        )

        return final_state
