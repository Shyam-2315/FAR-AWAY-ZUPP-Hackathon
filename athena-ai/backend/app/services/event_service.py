import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EventActivityType, EventStatus
from app.models.event import Event
from app.models.user import User
from app.repositories.event_repository import EventRepository
from app.schemas.events import EventCreate, EventFilters, EventUpdate


class EventServiceError(Exception):
    status_code = 400
    code = "EVENT_ERROR"


class EventNotFoundError(EventServiceError):
    status_code = 404
    code = "EVENT_NOT_FOUND"

    def __init__(self, event_id: uuid.UUID) -> None:
        super().__init__(f"Event {event_id} was not found")


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EventRepository(session)

    async def create_event(self, payload: EventCreate, actor: User) -> Event:
        event = Event(
            title=payload.title,
            description=payload.description,
            event_type=payload.event_type,
            severity=payload.severity,
            status=payload.status,
            source=payload.source,
            tenant_id=payload.tenant_id,
            event_metadata=payload.metadata,
            created_by=actor.id,
        )
        await self.repo.add(event)
        await self.repo.add_activity(
            event_id=event.id,
            activity_type=EventActivityType.CREATED,
            actor_id=actor.id,
            tenant_id=event.tenant_id,
            details={"status": event.status.value},
        )
        loaded = await self.repo.get_with_relations(event.id)
        if loaded is None:
            raise EventNotFoundError(event.id)
        return loaded

    async def list_events(self, filters: EventFilters) -> tuple[list[Event], int]:
        return await self.repo.list_events(filters)

    async def get_event(self, event_id: uuid.UUID) -> Event:
        event = await self.repo.get_with_relations(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        return event

    async def update_event(self, event_id: uuid.UUID, payload: EventUpdate, actor: User) -> Event:
        event = await self.repo.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError(event_id)

        changes = payload.model_dump(exclude_unset=True)
        metadata = changes.pop("metadata", None)
        for field, value in changes.items():
            setattr(event, field, value)
        if metadata is not None:
            event.event_metadata = metadata

        await self.session.flush()
        changed_fields = sorted([*changes.keys(), *(["metadata"] if metadata is not None else [])])
        await self.repo.add_activity(
            event_id=event.id,
            activity_type=EventActivityType.UPDATED,
            actor_id=actor.id,
            tenant_id=event.tenant_id,
            details={"fields": changed_fields},
        )
        loaded = await self.repo.get_with_relations(event.id)
        if loaded is None:
            raise EventNotFoundError(event_id)
        return loaded

    async def delete_event(self, event_id: uuid.UUID, actor: User) -> None:
        event = await self.repo.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        await self.repo.add_activity(
            event_id=event.id,
            activity_type=EventActivityType.UPDATED,
            actor_id=actor.id,
            tenant_id=event.tenant_id,
            details={"deleted": True},
        )
        await self.repo.soft_delete(event)

    async def record_workflow_activity(
        self,
        event_id: uuid.UUID,
        activity_type: EventActivityType,
        *,
        actor_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> Event:
        allowed = {
            EventActivityType.WORKFLOW_STARTED,
            EventActivityType.WORKFLOW_COMPLETED,
            EventActivityType.WORKFLOW_FAILED,
        }
        if activity_type not in allowed:
            msg = "activity_type must be a workflow activity"
            raise ValueError(msg)

        event = await self.repo.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError(event_id)

        if activity_type == EventActivityType.WORKFLOW_STARTED:
            event.status = EventStatus.PROCESSING
        elif activity_type == EventActivityType.WORKFLOW_COMPLETED:
            event.status = EventStatus.RESOLVED
        elif activity_type == EventActivityType.WORKFLOW_FAILED:
            event.status = EventStatus.FAILED

        await self.session.flush()
        await self.repo.add_activity(
            event_id=event.id,
            activity_type=activity_type,
            actor_id=actor_id,
            tenant_id=event.tenant_id,
            details=details or {},
        )
        loaded = await self.repo.get_with_relations(event.id)
        if loaded is None:
            raise EventNotFoundError(event_id)
        return loaded
