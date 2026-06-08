import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EventActivityType, EventSeverity, EventStatus
from app.models.event import Event, EventActivity


class EventActivityOut(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    activity_type: EventActivityType
    actor_id: uuid.UUID | None
    tenant_id: str | None
    details: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_activity(cls, activity: EventActivity) -> "EventActivityOut":
        return cls(
            id=activity.id,
            event_id=activity.event_id,
            activity_type=activity.activity_type,
            actor_id=activity.actor_id,
            tenant_id=activity.tenant_id,
            details=activity.details,
            created_at=activity.created_at,
        )


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    event_type: str = Field(..., min_length=1, max_length=100)
    severity: EventSeverity
    status: EventStatus = EventStatus.NEW
    source: str = Field(..., min_length=1, max_length=255)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "event_type", "source", "tenant_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    severity: EventSeverity | None = None
    status: EventStatus | None = None
    source: str | None = Field(default=None, min_length=1, max_length=255)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=100)
    metadata: dict[str, Any] | None = None

    @field_validator("title", "event_type", "source", "tenant_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class EventOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    event_type: str
    severity: EventSeverity
    status: EventStatus
    source: str
    tenant_id: str | None
    metadata: dict[str, Any]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    timeline: list[EventActivityOut] = Field(default_factory=list)

    @classmethod
    def from_event(cls, event: Event) -> "EventOut":
        return cls(
            id=event.id,
            title=event.title,
            description=event.description,
            event_type=event.event_type,
            severity=event.severity,
            status=event.status,
            source=event.source,
            tenant_id=event.tenant_id,
            metadata=event.event_metadata,
            created_by=event.created_by,
            created_at=event.created_at,
            updated_at=event.updated_at,
            timeline=[
                EventActivityOut.from_activity(activity)
                for activity in sorted(event.activities, key=lambda item: item.created_at)
            ],
        )


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    page_size: int


class EventFilters(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, min_length=1, max_length=200)
    severity: list[EventSeverity] | None = None
    event_type: list[str] | None = None
    status: list[EventStatus] | None = None
    tenant_id: str | None = Field(default=None, min_length=1, max_length=100)
    sort_by: Literal["created_at", "updated_at", "severity", "status", "event_type", "title"] = (
        "created_at"
    )
    sort_order: Literal["asc", "desc"] = "desc"
