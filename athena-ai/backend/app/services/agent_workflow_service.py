"""Agent workflow service — orchestrates the LangGraph pipeline for a given event.

Phase 3.2 complete: this version adds:
  1. stream_run() — async generator that yields AgentState snapshots after
     each node via LangGraph's .stream() API. Used by the SSE endpoint.
  2. Full persistence — after the pipeline completes, all agent outputs are
     written to PostgreSQL (WorkflowRun + Report rows) so nothing is lost.

Original run() is preserved unchanged for backwards compatibility.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.models.enums import EventActivityType
from app.models.report import Report
from app.models.user import User
from app.models.workflow_run import WorkflowRun
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


# Node name → human-readable label for the frontend progress UI
NODE_LABELS: dict[str, str] = {
    "observer": "Observer — Analysing signal",
    "investigation": "Investigator — Finding root cause",
    "prediction": "Predictor — Calculating exposure",
    "strategy": "Strategy Agent — Evaluating options",
    "decision": "Decision Engine — Choosing action",
    "reporting": "Reporting Agent — Writing summary",
}

# Ordered list matches the graph topology so progress % is deterministic
ORDERED_NODES = ["observer", "investigation", "prediction", "strategy", "decision", "reporting"]


class AgentWorkflowService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._event_svc = EventService(session)

    # ------------------------------------------------------------------ #
    # Original synchronous run() — kept for the existing POST endpoint
    # ------------------------------------------------------------------ #

    async def run(self, event_id: uuid.UUID, actor: User) -> AgentState:
        """Run the full multi-agent pipeline for the given event.

        Returns the final AgentState on success.
        Raises EventNotFoundError (→ 404) if the event does not exist.
        Raises WorkflowError (→ 500) if the pipeline fails after starting.
        """
        event = await self._event_svc.get_event(event_id)

        await self._event_svc.record_workflow_activity(
            event_id,
            EventActivityType.WORKFLOW_STARTED,
            actor_id=actor.id,
            details={"triggered_by": str(actor.id)},
        )

        started_at = datetime.now(UTC)

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

        try:
            workflow = get_workflow()
            final_state: AgentState = workflow.invoke(initial_state)  # type: ignore[attr-defined]
        except Exception as exc:
            error_msg = str(exc)
            await self._event_svc.record_workflow_activity(
                event_id,
                EventActivityType.WORKFLOW_FAILED,
                actor_id=actor.id,
                details={"error": error_msg},
            )
            raise WorkflowError(error_msg, event_id=event_id) from exc

        # Persist all outputs now that the pipeline completed successfully
        await self._persist_outputs(final_state, actor.id)

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

    # ------------------------------------------------------------------ #
    # New streaming run() — used by the SSE endpoint
    # ------------------------------------------------------------------ #

    async def stream_run(
        self,
        event_id: uuid.UUID,
        actor: User,
    ) -> AsyncGenerator[str, None]:
        """Stream agent outputs as Server-Sent Events (SSE).

        Yields one SSE-formatted string after each LangGraph node completes.
        The final event is a "done" message carrying the full WorkflowResponse.

        SSE format (each yield is a complete SSE message):
            data: {"node": "observer", "label": "...", "progress": 1,
                   "total": 6, "data": {...}, "errors": [...]}\\n\\n

        The frontend EventSource listener parses each message and updates
        the live progress UI node-by-node as they arrive.
        """
        # ── Fetch + validate event ──────────────────────────────────────
        event = await self._event_svc.get_event(event_id)

        await self._event_svc.record_workflow_activity(
            event_id,
            EventActivityType.WORKFLOW_STARTED,
            actor_id=actor.id,
            details={"triggered_by": str(actor.id), "mode": "stream"},
        )

        started_at = datetime.now(UTC)

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

        # ── Yield a "started" event so the frontend can show the panel ──
        yield _sse(
            "started",
            {
                "event_id": str(event_id),
                "event_title": event.title,
                "total_nodes": len(ORDERED_NODES),
            },
        )

        final_state: AgentState = initial_state
        completed_nodes: list[str] = []

        try:
            workflow = get_workflow()

            # Run LangGraph synchronously — it's pure CPU/mock logic with
            # no async DB calls inside agents, so .invoke() is safe here.
            # We use .stream() to get per-node chunks for SSE updates.
            # NOTE: Do NOT run in a thread executor — the async SQLAlchemy
            # session is not thread-safe and will corrupt on flush/commit.
            chunks: list[dict[str, Any]] = list(
                workflow.stream(initial_state)  # type: ignore[attr-defined]
            )

            # Process each chunk and yield an SSE event
            for chunk in chunks:
                for node_name, state_slice in chunk.items():
                    if node_name not in ORDERED_NODES:
                        continue

                    completed_nodes.append(node_name)
                    progress = len(completed_nodes)

                    # Merge slice into final_state so we accumulate outputs
                    if isinstance(state_slice, dict):
                        final_state = {**final_state, **state_slice}  # type: ignore[misc]

                    # Extract just this node's output for the SSE payload
                    node_output = _extract_node_output(node_name, state_slice)

                    yield _sse(
                        "node_complete",
                        {
                            "node": node_name,
                            "label": NODE_LABELS.get(node_name, node_name),
                            "progress": progress,
                            "total": len(ORDERED_NODES),
                            "data": node_output,
                            "errors": final_state.get("errors", []),
                        },
                    )

        except Exception as exc:
            error_msg = str(exc)
            # Roll back the session before any further DB operations
            # so the session is clean for the activity log write below.
            try:
                await self._session.rollback()
            except Exception:
                pass
            try:
                await self._event_svc.record_workflow_activity(
                    event_id,
                    EventActivityType.WORKFLOW_FAILED,
                    actor_id=actor.id,
                    details={"error": error_msg},
                )
            except Exception:
                pass
            yield _sse("error", {"message": error_msg, "event_id": str(event_id)})
            return

        # ── Persist all outputs to PostgreSQL ───────────────────────────
        await self._persist_outputs(final_state, actor.id)

        decision_out = final_state.get("decision")
        requires_approval = False
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

        # ── Yield the final "done" event with the complete WorkflowResponse
        report_out = final_state.get("report") or {}
        yield _sse(
            "done",
            {
                "event_id": str(event_id),
                "event_status": "RESOLVED",
                "observation": final_state.get("observation"),
                "investigation": final_state.get("investigation"),
                "prediction": final_state.get("prediction"),
                "strategies": final_state.get("strategies"),
                "decision": final_state.get("decision"),
                "report": report_out,
                "confidence_score": final_state.get("confidence_score", 0.0),
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "errors": final_state.get("errors", []),
            },
        )

    # ------------------------------------------------------------------ #
    # Persistence helper — called after both run() and stream_run()
    # ------------------------------------------------------------------ #

    async def _persist_outputs(
        self,
        final_state: AgentState,
        actor_id: uuid.UUID,
    ) -> None:
        """Write all agent outputs to PostgreSQL.

        Creates / updates two rows:
          - WorkflowRun: full JSONB snapshot of every agent output
          - Report: structured text fields for the Reporting Agent output
        """
        event_id: uuid.UUID = final_state["event_id"]
        report_out = final_state.get("report") or {}

        # WorkflowRun row — complete snapshot
        run = WorkflowRun(
            event_id=event_id,
            triggered_by=actor_id,
            observation=_jsonb_safe(final_state.get("observation")),
            investigation=_jsonb_safe(final_state.get("investigation")),
            prediction=_jsonb_safe(final_state.get("prediction")),
            strategies=_jsonb_safe(final_state.get("strategies")),
            decision=_jsonb_safe(final_state.get("decision")),
            overall_confidence=final_state.get("confidence_score", 0.0),
            status="COMPLETED",
            errors=final_state.get("errors", []),
            started_at=final_state.get("started_at"),
            completed_at=datetime.now(UTC),
        )
        self._session.add(run)

        # Report row — structured text fields from ReportOutput
        report = Report(
            event_id=event_id,
            executive_summary=report_out.get("executive_summary"),
            technical_summary=report_out.get("technical_summary"),
            recommended_action=report_out.get("recommended_action"),
            estimated_savings=report_out.get("estimated_savings"),
            confidence=report_out.get("confidence"),
        )
        self._session.add(report)

        # Commit directly here — the SSE StreamingResponse keeps the
        # connection open so the session dependency won't auto-commit
        # until the stream closes, which is too late.
        await self._session.commit()


# ------------------------------------------------------------------ #
# Private helpers
# ------------------------------------------------------------------ #


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event string.

    SSE wire format:
        event: <event_name>\\n
        data: <json_payload>\\n
        \\n
    """
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _jsonb_safe(value: Any) -> Any:
    """Ensure a value is JSON-serialisable before storing as JSONB."""
    if value is None:
        return None
    # Round-trip through JSON to catch uuid / datetime objects
    return json.loads(json.dumps(value, default=str))


def _extract_node_output(node_name: str, state_slice: Any) -> Any:
    """Pull just this node's output field from its state slice."""
    if not isinstance(state_slice, dict):
        return None
    field_map = {
        "observer": "observation",
        "investigation": "investigation",
        "prediction": "prediction",
        "strategy": "strategies",
        "decision": "decision",
        "reporting": "report",
    }
    field = field_map.get(node_name)
    return state_slice.get(field) if field else None