"""Rename event PROCESSING status to IN_PROGRESS.

Revision ID: 20250609_0004
Revises: 20250608_0003
Create Date: 2026-06-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20250609_0004"
down_revision: str | Sequence[str] | None = "20250608_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE event_status RENAME VALUE 'PROCESSING' TO 'IN_PROGRESS'")


def downgrade() -> None:
    op.execute("ALTER TYPE event_status RENAME VALUE 'IN_PROGRESS' TO 'PROCESSING'")
