# Database Architecture

Athena AI uses PostgreSQL as the durable source of truth for users, operational events, and the decision-intelligence lifecycle (investigation through reporting).

## Stack

| Layer | Technology |
| --- | --- |
| ORM | SQLAlchemy 2.0 (async) |
| Driver | `psycopg` 3 (`postgresql+psycopg://`) |
| Migrations | Alembic (async `env.py`) |
| Primary keys | UUID v4 |
| JSON fields | PostgreSQL `JSONB` |
| Enums | Native PostgreSQL `ENUM` types |

## Directory Layout

```
backend/
  alembic/                 # Migration environment and versions
  app/
    db/                    # Base, mixins, async engine/session
    models/                # SQLAlchemy ORM models and enums
    repositories/          # Async data-access layer
```

## Design Principles

1. **Repository-service boundary** — HTTP routers stay thin; repositories encapsulate queries and persistence. Business services will compose repositories in later phases.
2. **API-ready shapes** — Models map cleanly to flat Pydantic response schemas. Child entities reference `event_id` rather than embedding full parent graphs to avoid circular JSON.
3. **Soft delete** — `User` and `Event` include `deleted_at`. Repositories filter active rows by default and expose `include_deleted` for admin flows.
4. **Audit-friendly timestamps** — `created_at` / `updated_at` mixins on mutable domain roots; child workflow artifacts are append-only with `created_at`.
5. **Referential integrity** — `events.created_by → users.id` uses `RESTRICT`. Workflow children use `CASCADE` when an event is hard-deleted.

## Entity Overview

### `users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `name` | VARCHAR(255) | |
| `email` | VARCHAR(320) | Indexed; partial unique index where `deleted_at IS NULL` |
| `password_hash` | VARCHAR(255) | |
| `role` | `user_role` ENUM | `ADMIN`, `MANAGER`, `ANALYST`, `VIEWER` |
| `is_active` | BOOLEAN | |
| `created_at`, `updated_at` | TIMESTAMPTZ | Server defaults |
| `deleted_at` | TIMESTAMPTZ | Soft delete |

### `events`

Central aggregate for the decision workflow.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID PK | |
| `title` | VARCHAR(500) | |
| `description` | TEXT | Optional |
| `event_type` | VARCHAR(100) | Domain-specific classifier |
| `severity` | `event_severity` ENUM | `LOW` … `CRITICAL` |
| `status` | `event_status` ENUM | `NEW`, `IN_PROGRESS`, `RESOLVED`, `FAILED` |
| `source` | VARCHAR(255) | Originating system |
| `metadata` | JSONB | Flexible event context (ORM attribute: `event_metadata`) |
| `created_by` | UUID FK → `users.id` | `RESTRICT` on delete |
| `created_at`, `updated_at`, `deleted_at` | TIMESTAMPTZ | |

Indexes: `status`, `severity`, `created_by`, `created_at`.

### Workflow children (1:N from `events`)

All child tables:

- Use UUID primary keys
- Reference `events.id` with `ON DELETE CASCADE`
- Index `event_id`
- Store `created_at` only (append-only artifacts)

| Table | Purpose | Notable columns |
| --- | --- | --- |
| `investigations` | Root-cause analysis | `evidence` JSONB, `confidence` |
| `predictions` | Risk scoring | `revenue_risk`, `delay_probability`, `churn_probability` |
| `recommendations` | Suggested actions | `effort` ENUM, `estimated_savings` |
| `decisions` | Selected action | `selected_action` JSONB, `requires_human_approval` |
| `reports` | Generated narratives | `report_type`, `report_text` |

## Async Session Usage

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.event_repository import EventRepository

async def example(session: AsyncSession = Depends(get_db_session)):
    repo = EventRepository(session)
    event = await repo.get_with_relations(event_id)
```

`get_db_session` commits on success and rolls back on exception.

## Migrations

From `backend/`:

```bash
alembic upgrade head          # Apply all migrations
alembic revision --autogenerate -m "description"  # Generate new revision
alembic downgrade -1          # Roll back one revision
```

Initial migration: `20250608_0001_initial_schema`.

## Health Check

`GET /health/db` executes `SELECT 1` through the async session and returns connection latency in milliseconds. Use this for database-specific probes; `/healthz` remains a process liveness check.

## Local Development Notes

- Docker Compose maps PostgreSQL to host port **5433** by default so it does not conflict with a system PostgreSQL install on port 5432.
- On Windows, Alembic and pytest set `WindowsSelectorEventLoopPolicy` because `psycopg` async mode is incompatible with the default `ProactorEventLoop`.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://…@localhost:5433/athena` | Async SQLAlchemy URL |
| `DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Burst connections |
| `DATABASE_ECHO` | `false` | SQL debug logging |

## Frontend Integration (Lovable.dev)

When exposing REST resources:

- Return flat DTOs per entity (e.g. `EventResponse`, `InvestigationResponse`).
- Use explicit foreign-key UUIDs (`event_id`, `created_by`) instead of nested object graphs.
- Serialize enums as string values matching PostgreSQL enum labels.
- Serialize UUIDs and timestamps as strings (ISO 8601 for datetimes).

This keeps generated frontend types predictable and avoids circular JSON structures.
