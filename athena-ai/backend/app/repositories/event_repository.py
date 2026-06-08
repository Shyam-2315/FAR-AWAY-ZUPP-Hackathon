import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import EventActivityType, EventStatus
from app.models.event import Event, EventActivity
from app.repositories.base import BaseRepository
from app.schemas.events import EventFilters


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Event)

    async def get_with_relations(self, event_id: uuid.UUID) -> Event | None:
        query = (
            select(Event)
            .where(Event.id == event_id)
            .where(Event.deleted_at.is_(None))
            .options(
                selectinload(Event.creator),
                selectinload(Event.activities),
                selectinload(Event.investigations),
                selectinload(Event.predictions),
                selectinload(Event.recommendations),
                selectinload(Event.decisions),
                selectinload(Event.reports),
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_activity(
        self,
        *,
        event_id: uuid.UUID,
        activity_type: EventActivityType,
        actor_id: uuid.UUID | None,
        tenant_id: str | None,
        details: dict[str, object],
    ) -> EventActivity:
        activity = EventActivity(
            event_id=event_id,
            activity_type=activity_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            details=details,
        )
        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)
        return activity

    async def list_events(self, filters: EventFilters) -> tuple[list[Event], int]:
        base_query = self._apply_filters(select(Event).where(Event.deleted_at.is_(None)), filters)
        count_query = select(func.count()).select_from(base_query.order_by(None).subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        sort_column = {
            "created_at": Event.created_at,
            "updated_at": Event.updated_at,
            "severity": Event.severity,
            "status": Event.status,
            "event_type": Event.event_type,
            "title": Event.title,
        }[filters.sort_by]
        order_clause = sort_column.asc() if filters.sort_order == "asc" else sort_column.desc()

        query = (
            base_query.options(selectinload(Event.activities))
            .order_by(order_clause, Event.id.asc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(query)
        return list(result.scalars().unique().all()), total

    def _apply_filters(
        self,
        query: Select[tuple[Event]],
        filters: EventFilters,
    ) -> Select[tuple[Event]]:
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            query = query.where(
                or_(
                    Event.title.ilike(pattern),
                    Event.description.ilike(pattern),
                    Event.event_type.ilike(pattern),
                    Event.source.ilike(pattern),
                )
            )
        if filters.severity:
            query = query.where(Event.severity.in_(filters.severity))
        if filters.event_type:
            query = query.where(Event.event_type.in_(filters.event_type))
        if filters.status:
            query = query.where(Event.status.in_(filters.status))
        if filters.tenant_id:
            query = query.where(Event.tenant_id == filters.tenant_id)
        return query

    async def list_by_status(self, status: EventStatus) -> list[Event]:
        query = (
            select(Event)
            .where(Event.deleted_at.is_(None))
            .where(Event.status == status)
            .order_by(Event.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
