"""Server-Sent Events (SSE) streaming endpoint for the agent workflow.

GET /api/agents/stream/{event_id}
    Opens a persistent HTTP connection and streams one SSE event per
    LangGraph node as it completes.  The frontend EventSource listener
    receives each chunk and updates the live progress UI in real time.

Why SSE instead of WebSockets?
  - One-way stream (server → client) is all we need here.
  - Works through standard HTTP/1.1 — no protocol upgrade needed.
  - Natively supported by browsers via the EventSource API.
  - Automatic reconnection built into the browser's EventSource.
  - Far simpler to implement and deploy than WebSockets.

Event sequence:
  1. "started"       — workflow is beginning, sends event metadata
  2. "node_complete" — fires after each of the 6 agent nodes completes
  3. "done"          — full WorkflowResponse payload, workflow finished
  4. "error"         — fires if the pipeline throws (instead of "done")

Authentication:
  The EventSource API cannot set custom headers, so the JWT is passed
  as a query parameter (?token=<jwt>) and validated here manually using
  the same TokenService used everywhere else.
"""

from __future__ import annotations

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_token_service
from app.db.session import get_db_session
from app.repositories.user_repository import UserRepository
from app.services.agent_workflow_service import AgentWorkflowService, WorkflowError
from app.services.event_service import EventNotFoundError
from app.services.token_service import TokenService

router = APIRouter(prefix="/agents", tags=["agents-stream"])


async def _resolve_user_from_token(
    token: str,
    token_service: TokenService,
    session: AsyncSession,
) -> object:
    """Validate the JWT query param and return the User ORM object.

    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    try:
        payload = token_service.decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    users = UserRepository(session)
    user = await users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated.",
        )
    return user


@router.get(
    "/stream/{event_id}",
    summary="Stream the multi-agent workflow as Server-Sent Events",
    description=(
        "Opens a persistent HTTP connection and streams one SSE message per "
        "LangGraph node as it completes. Pass the JWT as ?token=<access_token> "
        "because the browser EventSource API cannot set Authorization headers. "
        "Events: started | node_complete (×6) | done | error."
    ),
    response_class=StreamingResponse,
)
async def stream_workflow(
    event_id: uuid.UUID,
    token: Annotated[str, Query(description="JWT access token (EventSource cannot set headers)")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> StreamingResponse:
    # Validate JWT and resolve user manually (EventSource can't send headers)
    user = await _resolve_user_from_token(token, token_service, session)

    svc = AgentWorkflowService(session)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in svc.stream_run(event_id, user):  # type: ignore[arg-type]
                yield chunk
            # SSE comment line — not shown to the browser but flushes the
            # TCP buffer and causes the HTTP response body to close cleanly.
            # Without this the browser's EventSource sees an abrupt close
            # and automatically reconnects, causing the infinite loop.
            yield ": stream-end\n\n"
        except EventNotFoundError as exc:
            import json
            yield f"event: error\ndata: {json.dumps({'message': str(exc), 'code': 'EVENT_NOT_FOUND'})}\n\n"
            yield ": stream-end\n\n"
        except WorkflowError as exc:
            import json
            yield f"event: error\ndata: {json.dumps({'message': str(exc), 'code': 'WORKFLOW_FAILED'})}\n\n"
            yield ": stream-end\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent any proxy or CDN from buffering the SSE stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            # Allow the frontend origin to read this response
            "Access-Control-Allow-Origin": "*",
        },
    )