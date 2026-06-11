"""Fix report table and persist full agent outputs.

Revision ID: 002_fix_report_agent_outputs
Revises: 001  (update this to your actual previous revision ID)
Create Date: 2026-01-01 00:00:00.000000

What this migration does:
  1. Drops the old generic report columns (report_type, report_text) that
     did not match the actual AgentState.report shape.
  2. Adds structured columns that exactly mirror ReportOutput / AgentState
     so every agent's output is persisted to PostgreSQL after a workflow run.
  3. Adds a workflow_runs table that stores the complete AgentState snapshot
     (observation, investigation, prediction, strategies, decision) as JSONB
     so nothing is lost between requests.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# ── Revision identifiers ───────────────────────────────────────────────────
revision = "002_fix_report_agent_outputs"
down_revision = "20250609_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Fix the reports table
    #    Old shape: report_type (str), report_text (str), confidence (float)
    #    New shape: mirrors ReportOutput TypedDict exactly
    # ------------------------------------------------------------------ #
    op.drop_column("reports", "report_type")
    op.drop_column("reports", "report_text")

    # Core report fields from ReportOutput
    op.add_column(
        "reports",
        sa.Column("executive_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("technical_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("recommended_action", sa.Text(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("estimated_savings", sa.Float(), nullable=True),
    )
    # confidence already exists — just make it non-nullable with a default
    op.alter_column(
        "reports",
        "confidence",
        existing_type=sa.Float(),
        nullable=True,
        server_default="0.0",
    )

    # ------------------------------------------------------------------ #
    # 2. Create workflow_runs table
    #    Stores the complete AgentState snapshot so every agent output
    #    (observation, investigation, prediction, strategies, decision)
    #    survives beyond the request lifecycle.
    # ------------------------------------------------------------------ #
    op.create_table(
        "workflow_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Full agent outputs stored as JSONB — queryable and schema-flexible
        sa.Column("observation", JSONB, nullable=True),
        sa.Column("investigation", JSONB, nullable=True),
        sa.Column("prediction", JSONB, nullable=True),
        sa.Column("strategies", JSONB, nullable=True),
        sa.Column("decision", JSONB, nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="COMPLETED"),
        sa.Column("errors", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_runs_event_id", "workflow_runs", ["event_id"])
    op.create_index("ix_workflow_runs_triggered_by", "workflow_runs", ["triggered_by"])
    op.create_index("ix_workflow_runs_created_at", "workflow_runs", ["created_at"])


def downgrade() -> None:
    # Reverse workflow_runs
    op.drop_index("ix_workflow_runs_created_at", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_triggered_by", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_event_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

    # Reverse reports table changes
    op.drop_column("reports", "estimated_savings")
    op.drop_column("reports", "recommended_action")
    op.drop_column("reports", "technical_summary")
    op.drop_column("reports", "executive_summary")
    op.add_column(
        "reports",
        sa.Column("report_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "reports",
        sa.Column("report_type", sa.String(100), nullable=False, server_default=""),
    )