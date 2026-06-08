"""Event engine timeline and tenant-ready indexes.

Revision ID: 20250608_0003
Revises: 20250608_0002
Create Date: 2025-06-08 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20250608_0003"
down_revision: str | Sequence[str] | None = "20250608_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

event_activity_type_enum = postgresql.ENUM(
    "CREATED",
    "UPDATED",
    "WORKFLOW_STARTED",
    "WORKFLOW_COMPLETED",
    "WORKFLOW_FAILED",
    name="event_activity_type",
    create_type=False,
)


def upgrade() -> None:
    event_activity_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("events", sa.Column("tenant_id", sa.String(length=100), nullable=True))
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)
    op.create_index("ix_events_tenant_id", "events", ["tenant_id"], unique=False)

    op.create_table(
        "event_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", event_activity_type_enum, nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.String(length=100), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_activities_activity_type",
        "event_activities",
        ["activity_type"],
        unique=False,
    )
    op.create_index(
        "ix_event_activities_created_at",
        "event_activities",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_event_activities_event_id",
        "event_activities",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_activities_event_id", table_name="event_activities")
    op.drop_index("ix_event_activities_created_at", table_name="event_activities")
    op.drop_index("ix_event_activities_activity_type", table_name="event_activities")
    op.drop_table("event_activities")

    op.drop_index("ix_events_tenant_id", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_column("events", "tenant_id")

    event_activity_type_enum.drop(op.get_bind(), checkfirst=True)
