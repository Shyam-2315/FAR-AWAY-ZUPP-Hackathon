# Athena AI

Athena AI is an Autonomous Decision Intelligence Platform. This repository is a production-oriented monorepo scaffold for the backend, frontend, documentation, infrastructure, and developer automation.

## What Was Added

- Monorepo structure with `backend/`, `frontend/`, `docs/`, `infra/`, and `scripts/`.
- FastAPI backend with typed settings, async SQLAlchemy 2.0, Alembic migrations, and repository layer.
- PostgreSQL decision-intelligence schema: users, events, investigations, predictions, recommendations, decisions, and reports.
- **Enterprise-grade JWT authentication and RBAC** — register, login, refresh, logout, `/me`, role guards, refresh-token rotation, token revocation, and audit logging.
- **Production-grade Event Management Engine** with JWT-protected CRUD APIs, RBAC, pagination, filtering, sorting, search, tenant-ready fields, and event timeline activity tracking.
- **Frontend-ready CORS** — `FRONTEND_ORIGINS` env variable accepts comma-separated origins for Vite, Next.js, or any dev port.
- **Phase 3.1 — LangGraph Multi-Agent Workflow Skeleton** — deterministic 6-agent pipeline (Observer → Investigation → Prediction → Strategy → Decision → Reporting) exposed via `POST /api/agents/run/{event_id}`. Event status lifecycle managed (PROCESSING → RESOLVED/FAILED). Full workflow JSON returned to the frontend.
- Lovable-generated React/Vite + TanStack Router frontend in `frontend/athena-ai-dashboard-main`.
- PostgreSQL and Redis local dependency stack through Docker Compose.
- Root `.env.example`, `.gitignore`, `AGENTS.md`, and full `docs/` suite.
- Backend tests for health endpoints, database health, migrations, constraints, relationships, full auth flow, event CRUD, frontend integration contracts, and agent workflow.

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
source .venv/bin/activate        # Linux/macOS
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

If port `8000` is already held by a stale process on Windows PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

Start the correct backend from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run the frontend:

```bash
cd frontend/athena-ai-dashboard-main
npm install
npm run dev
```

Default local URLs:

- Frontend (Lovable Vite): `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

## Lovable.dev Frontend Integration

The Lovable.dev React/Vite frontend is wired to the backend API client in `frontend/athena-ai-dashboard-main/src/lib/api.ts`.

**Frontend environment variable (`.env.local` in the frontend project):**

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

**Backend CORS is pre-configured for all common local dev ports:**

```dotenv
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080
```

To add a Lovable.dev preview or production URL:

```dotenv
FRONTEND_ORIGINS=http://localhost:5173,https://your-app.lovable.app
```

See `docs/FRONTEND_INTEGRATION.md` for the full integration guide including auth flow patterns, refresh token handling, and TypeScript examples.

See `docs/LOVABLE_API_CONTRACTS.md` for exact request/response shapes, query parameters, error formats, and TypeScript type sketches for every endpoint.

Working integrated flow:

1. Register or login.
2. Open the protected dashboard.
3. Create, list, view, edit, and delete events.
4. Run the AI workflow from an event detail page.
5. Review the workflow response or a clean fallback if the endpoint is unavailable.
6. Logout from the topbar or settings page.

The frontend self-register flow requests a `MANAGER` demo role so event creation, deletion, and workflow execution work end-to-end in local hackathon/demo environments. Backend RBAC still enforces role requirements on every endpoint.

## Local Frontend/Backend Connection Checks

Expected local frontend env values:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Expected local auth URLs:

- `POST http://localhost:8000/api/auth/register`
- `POST http://localhost:8000/api/auth/login`
- `GET  http://localhost:8000/api/auth/me`
- `POST http://localhost:8000/api/auth/refresh`
- `POST http://localhost:8000/api/auth/logout`

Run the integration checker from the repo root:

```powershell
.\scripts\check-local-integration.ps1
```

It checks the port `8000` listener, `GET http://localhost:8000/healthz`, `GET http://localhost:8000/openapi.json`, confirms `/api/auth/register` is published in OpenAPI, and prints the frontend `VITE_API_BASE_URL`.

Troubleshooting:

- Backend unreachable: `GET /healthz` fails or the browser reports it cannot reach `http://localhost:8000`. Kill stale port `8000` processes, start `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` from `backend/`, then retry `.\scripts\check-local-integration.ps1`.
- CORS error: `/healthz` succeeds from PowerShell, but the browser blocks frontend requests. Set `FRONTEND_ORIGINS` to include the active frontend origin, for example `http://localhost:5173`, and restart the backend. Do not use `*` in production.
- 404 wrong endpoint: `openapi.json` does not list the route the frontend is calling, or the browser shows a 404. Confirm the frontend base URL has no `/api` suffix and auth calls use `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, and `/api/auth/logout`.
- 422 validation error: the backend was reached, but the request body does not match the Pydantic schema. Check the response `detail` field and the submitted form fields.
- 500 backend error: the route exists and the backend was reached, but server-side code failed. Check the FastAPI terminal logs and database connectivity.

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

- `POST /api/events` — create an event (requires `ANALYST` or above).
- `GET /api/events` — list events with pagination, filtering, search, sorting (requires `VIEWER` or above).
- `GET /api/events/{event_id}` — fetch one event with timeline (requires `VIEWER` or above).
- `PATCH /api/events/{event_id}` — update an event (requires `ANALYST` or above).
- `DELETE /api/events/{event_id}` — soft-delete an event (requires `MANAGER` or above).

Event list response:

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

### Agent Workflow (`/api/agents`)

- `POST /api/agents/run/{event_id}` — run the full multi-agent pipeline (requires `ANALYST` or above).

**Example request:**

```bash
curl -X POST http://localhost:8000/api/agents/run/<event_id> \
  -H "Authorization: Bearer <access_token>"
```

**Example response structure:**

```json
{
  "event_id": "...",
  "event_status": "RESOLVED",
  "observation":   { "summary": "...", "detected_type": "...", "priority": "...", "risk_indicators": [], "confidence": 0.85 },
  "investigation": { "root_cause": "...", "impact": "...", "evidence": [], "confidence": 0.80 },
  "prediction":    { "revenue_risk": 125000.0, "delay_probability": 0.72, "churn_probability": 0.18, "severity_score": 7.5, "confidence": 0.78 },
  "strategies":    [ { "title": "...", "description": "...", "estimated_savings": 85000.0, "effort": "MEDIUM", "risk_reduction": 0.65, "confidence": 0.82 } ],
  "decision":      { "selected_action": {}, "decision_reason": "...", "expected_savings": 85000.0, "confidence": 0.82, "requires_human_approval": false },
  "report":        { "executive_summary": "...", "technical_summary": "...", "recommended_action": "...", "estimated_savings": 85000.0, "confidence": 0.81 },
  "confidence_score": 0.81,
  "started_at": "2026-06-08T12:00:00Z",
  "completed_at": "2026-06-08T12:00:01Z",
  "errors": []
}
```

The workflow:
1. Fetches the event (404 if missing).
2. Sets status → `PROCESSING`, records `WORKFLOW_STARTED` activity.
3. Runs 6 LangGraph agents in sequence.
4. On success: status → `RESOLVED`, records `WORKFLOW_COMPLETED`.
5. On failure: status → `FAILED`, records `WORKFLOW_FAILED`.

`requires_human_approval` is `true` when severity is `CRITICAL`, confidence < 0.75, or expected savings > $500k.

## Commands

Backend:

- `alembic upgrade head` — applies database migrations.
- `alembic revision --autogenerate -m "description"` — creates a new migration.
- `uvicorn app.main:app --reload` — starts the FastAPI development server.
- `pytest` — runs all backend tests (requires PostgreSQL via Docker Compose).
- `ruff check .` — runs backend linting.
- `mypy .` — runs backend type checking.

Frontend:

- `npm run dev` — starts the Lovable Vite development server.
- `npm run build` — builds the frontend.
- `npm run lint` — runs linting.
- No separate `typecheck` script exists; `npm run build` performs TypeScript build validation.

## Environment Variables

See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080` | Comma-separated allowed CORS origins for the frontend |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Legacy single-origin CORS variable (merged with `FRONTEND_ORIGINS`) |
| `JWT_SECRET_KEY` | *(must be set)* | HS256 signing secret, min 32 chars |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API base URL (Vite) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend API base URL (Next.js) |

If the browser shows CORS or network errors, confirm the backend is running on `http://localhost:8000`, `VITE_API_BASE_URL` matches that URL, and `FRONTEND_ORIGINS` includes the active Vite origin such as `http://localhost:5173`.

## Database

PostgreSQL schema and migration details:

- `docs/DATABASE_ARCHITECTURE.md` — stack, entities, repositories, and API integration guidance.
- `docs/ER_DIAGRAM.md` — entity-relationship diagram and index summary.
- `docs/AUTH_FLOW.md` — authentication and token lifecycle diagrams.
- `docs/EVENT_ENGINE.md` — event API, timeline, RBAC, filters, and service architecture.
- `docs/FRONTEND_INTEGRATION.md` — full guide for connecting a Lovable.dev / Vite / Next.js frontend.
- `docs/LOVABLE_API_CONTRACTS.md` — exact API contracts with request/response shapes and TypeScript types.
- `docs/SECURITY.md` — security architecture, threat model, and hardening notes.

Core tables: `users`, `events`, `event_activities`, `investigations`, `predictions`, `recommendations`, `decisions`, `reports`, `refresh_tokens`, `audit_logs`.

## Testing Status

- Backend: `pytest` covers `/healthz`, `/health/db`, Alembic migrations, FK/unique constraints, ORM relationships, soft-delete filtering, full auth flow, event CRUD/pagination/filtering/RBAC, frontend integration contracts, and the Phase 3.1 LangGraph workflow endpoint.
- Latest local validation on 2026-06-09: backend `ruff` passed; backend `mypy` passed with no issues in 66 source files. Backend `pytest` and `alembic current` were blocked because PostgreSQL was not reachable on `localhost:5433`.
- Frontend: `npm run build` passes; `npm run lint` passes with shadcn fast-refresh warnings only.
- LangGraph workflow integration tests: added for success, auth/RBAC, missing events, status transitions, activities, response sections, decision selection, confidence, and critical-event approval.

## Roles

| Role | Description |
|---|---|
| `ADMIN` | Full platform access |
| `MANAGER` | Manage events and workflows |
| `ANALYST` | Create and update events and investigations |
| `VIEWER` | Read-only access |

## Next Recommended Step

Phase 3.2 should persist workflow outputs into the existing `investigations`, `predictions`, `recommendations`, `decisions`, and `reports` tables behind service/repository interfaces while preserving the current JSON response contract for the frontend.
