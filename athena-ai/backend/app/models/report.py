"""Report ORM model — stores the Reporting Agent's structured output.

Mirrors ReportOutput from app.agents.state exactly so there is no
impedance mismatch between the AgentState and what gets persisted.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.event import Event


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_event_id", "event_id"),)

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

    # ── Structured agent output fields (mirror ReportOutput TypedDict) ── #
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship("Event", back_populates="reports", lazy="selectin")