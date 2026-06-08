import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_role
from app.db.session import get_db_session
from app.models.enums import EventSeverity, EventStatus, UserRole
from app.models.user import User
from app.schemas.events import EventCreate, EventFilters, EventListOut, EventOut, EventUpdate
from app.services.event_service import EventService, EventServiceError

router = APIRouter(prefix="/events", tags=["events"])


def _error_detail(exc: EventServiceError) -> dict[str, str]:
    return {"code": exc.code, "message": str(exc)}


@router.post(
    "",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an event",
)
async def create_event(
    body: EventCreate,
    current_user: Annotated[User, Depends(require_min_role(UserRole.ANALYST))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventOut:
    service = EventService(session)
    try:
        event = await service.create_event(body, current_user)
    except EventServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_detail(exc)) from exc
    return EventOut.from_event(event)


@router.get(
    "",
    response_model=EventListOut,
    summary="List events with pagination, filtering, search, and sorting",
)
async def list_events(
    current_user: Annotated[User, Depends(require_min_role(UserRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    severity: Annotated[list[EventSeverity] | None, Query()] = None,
    event_type: Annotated[list[str] | None, Query(min_length=1, max_length=100)] = None,
    status_filter: Annotated[list[EventStatus] | None, Query(alias="status")] = None,
    tenant_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    sort_by: Annotated[
        Literal["created_at", "updated_at", "severity", "status", "event_type", "title"],
        Query(),
    ] = "created_at",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> EventListOut:
    _ = current_user
    filters = EventFilters(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        event_type=event_type,
        status=status_filter,
        tenant_id=tenant_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    service = EventService(session)
    items, total = await service.list_events(filters)
    return EventListOut(
        items=[EventOut.from_event(event) for event in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get an event by id",
)
async def get_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_min_role(UserRole.VIEWER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventOut:
    _ = current_user
    service = EventService(session)
    try:
        event = await service.get_event(event_id)
    except EventServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_detail(exc)) from exc
    return EventOut.from_event(event)


@router.patch(
    "/{event_id}",
    response_model=EventOut,
    summary="Update an event",
)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    current_user: Annotated[User, Depends(require_min_role(UserRole.ANALYST))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EventOut:
    service = EventService(session)
    try:
        event = await service.update_event(event_id, body, current_user)
    except EventServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_detail(exc)) from exc
    return EventOut.from_event(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an event",
)
async def delete_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_min_role(UserRole.MANAGER))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    service = EventService(session)
    try:
        await service.delete_event(event_id, current_user)
    except EventServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_detail(exc)) from exc
