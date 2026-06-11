"""WorkflowRun ORM model — persists the complete AgentState snapshot.

Every agent output (observation, investigation, prediction, strategies,
decision) is stored as JSONB so nothing is lost between requests and
the Reports page can read structured data from PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_event_id", "event_id"),
        Index("ix_workflow_runs_triggered_by", "triggered_by"),
        Index("ix_workflow_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Full agent outputs as JSONB (queryable, schema-flexible) ──────── #
    observation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    investigation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    prediction: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    strategies: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")
    errors: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship("Event", lazy="selectin")
    actor: Mapped["User | None"] = relationship("User", lazy="selectin")