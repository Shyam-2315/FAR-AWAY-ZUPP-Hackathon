# Athena AI

Athena AI is an Autonomous Decision Intelligence Platform. This repository is a production-oriented monorepo scaffold for the backend, frontend, documentation, infrastructure, and developer automation.

## What Was Added

- Monorepo structure with `backend/`, `frontend/`, `docs/`, `infra/`, and `scripts/`.
- FastAPI backend with typed settings, async SQLAlchemy 2.0, Alembic migrations, and repository layer.
- PostgreSQL decision-intelligence schema: users, events, investigations, predictions, recommendations, decisions, and reports.
- **Enterprise-grade JWT authentication and RBAC** — register, login, refresh, logout, `/me`, role guards, refresh-token rotation, token revocation, and audit logging.
- **Production-grade Event Management Engine** with JWT-protected CRUD APIs, RBAC, pagination, filtering, sorting, search, tenant-ready fields, and event timeline activity tracking.
- Next.js + TypeScript + Tailwind CSS frontend scaffold.
- PostgreSQL and Redis local dependency stack through Docker Compose.
- Root `.env.example`, `.gitignore`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/AUTH_FLOW.md`, `docs/DATABASE_ARCHITECTURE.md`, `docs/ER_DIAGRAM.md`, `docs/ROADMAP.md`, and `docs/SECURITY.md`.
- Backend tests for health endpoints, database health, migrations, constraints, relationships, and full auth flow.

## How To Run It

Copy the example environment file:

```bash
cp .env.example .env
```

Set a secure JWT secret in `.env`:

```dotenv
JWT_SECRET_KEY=<random 32+ character string>
```

Start local infrastructure:

```bash
docker compose up -d
```

Run the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## API Endpoints

### Health

- `GET /healthz` — process health check.
- `GET /readyz` — dependency readiness placeholder.
- `GET /health/db` — PostgreSQL connectivity check with round-trip latency.

### Auth (`/api/auth`)

- `POST /api/auth/register` — create an account, returns token pair + user.
- `POST /api/auth/login` — authenticate, returns token pair + user.
- `POST /api/auth/refresh` — rotate refresh token, returns new token pair + user.
- `POST /api/auth/logout` — revoke refresh token (requires Bearer access token).
- `GET  /api/auth/me` — return current user profile (requires Bearer access token).

All token responses use the Lovable.dev-compatible envelope:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": { "id": "...", "name": "...", "email": "...", "role": "...", "is_active": true, "created_at": "..." }
}
```

### Events (`/api/events`)

- `POST /api/events` - create an event (requires `ANALYST` or above).
- `GET /api/events` - list events (requires `VIEWER` or above).
- `GET /api/events/{event_id}` - fetch one event with timeline (requires `VIEWER` or above).
- `PATCH /api/events/{event_id}` - update an event (requires `ANALYST` or above).
- `DELETE /api/events/{event_id}` - soft-delete an event (requires `MANAGER` or above).

The list response is dashboard-ready:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

Supported list query parameters: `page`, `page_size`, `search`, `severity`, `event_type`, `status`, `tenant_id`, `sort_by`, and `sort_order`.

## Commands

Backend:

- `alembic upgrade head` — applies database migrations.
- `alembic revision --autogenerate -m "description"` — creates a new migration.
- `uvicorn app.main:app --reload` — starts the FastAPI development server.
- `pytest` — runs all backend tests (requires PostgreSQL via Docker Compose).
- `ruff check .` — runs backend linting.
- `mypy app` — runs backend type checking.

Frontend:

- `npm run dev` — starts the Next.js development server.
- `npm run build` — builds the frontend.
- `npm run lint` — runs Next.js linting.
- `npm run typecheck` — runs TypeScript type checking.

## Environment Variables

See `.env.example` for the full list. Auth-specific variables:

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | *(must be set)* | HS256 signing secret, min 32 chars |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

## Database

PostgreSQL schema and migration details:

- `docs/DATABASE_ARCHITECTURE.md` — stack, entities, repositories, and API integration guidance.
- `docs/ER_DIAGRAM.md` — entity-relationship diagram and index summary.
- `docs/AUTH_FLOW.md` — authentication and token lifecycle diagrams.
- `docs/EVENT_ENGINE.md` - event API, timeline, RBAC, filters, and service architecture.
- `docs/API_CONTRACTS.md` - public backend API contracts for auth and events.
- `docs/SECURITY.md` — security architecture, threat model, and hardening notes.

Core tables: `users`, `events`, `event_activities`, `investigations`, `predictions`, `recommendations`, `decisions`, `reports`, `refresh_tokens`, `audit_logs`.

## Testing Status

- Backend: `pytest` covers `/healthz`, `/health/db`, Alembic migrations, FK/unique constraints, ORM relationships, soft-delete filtering, the full auth flow (register, login, refresh rotation, revocation, logout, RBAC, expired/invalid/tampered tokens), and event CRUD/pagination/filtering/auth/invalid payload flows.
- Frontend: no tests have been added yet.
- LangGraph workflow integration tests: not added yet.

## Roles

| Role | Description |
|---|---|
| `ADMIN` | Full platform access |
| `MANAGER` | Manage workflows and users |
| `ANALYST` | Create and review investigations |
| `VIEWER` | Read-only access |

## Next Recommended Step

Define the first decision workflow contract and expose thin REST endpoints that return flat, JSON-serializable DTOs for the Lovable.dev frontend. Protect those routes with `Depends(require_min_role(UserRole.ANALYST))` from `app.api.deps`. Wire LangGraph nodes to the existing repositories for investigation → prediction → recommendation → decision → report persistence.
