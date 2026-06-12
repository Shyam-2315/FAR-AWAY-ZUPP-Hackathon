# Athena AI

Athena AI is an Autonomous Decision Intelligence Platform. Given an operational event (a security alert, service incident, fraud signal, etc.), a six-agent AI pipeline observes, investigates, predicts financial impact, proposes mitigation strategies, makes a decision, and writes an executive + technical report — streamed live to the dashboard and exported as a PDF.

This repository is a production-oriented monorepo containing the backend, frontend, documentation, infrastructure, and developer automation.

## What's Included

- Monorepo structure with `backend/`, `frontend/`, `docs/`, `infra/`, and `scripts/`.
- FastAPI backend with typed settings, async SQLAlchemy 2.0, Alembic migrations, and repository layer.
- PostgreSQL decision-intelligence schema: users, events, event activities, workflow runs, reports, refresh tokens, audit logs.
- **Enterprise-grade JWT authentication and RBAC** — register, login, refresh, logout, `/me`, role guards, refresh-token rotation, token revocation, and audit logging.
- **Production-grade Event Management Engine** with JWT-protected CRUD APIs, RBAC, pagination, filtering, sorting, search, tenant-ready fields, and event timeline activity tracking.
- **Frontend-ready CORS** — `FRONTEND_ORIGINS` env variable accepts comma-separated origins for Vite, Next.js, or any dev port.
- **Multi-agent LangGraph pipeline (Observer → Investigation → Prediction → Strategy → Decision → Reporting)**, now powered by real Claude (Anthropic) API calls for the LLM-driven agents, with deterministic mock fallbacks if no API key is configured.
- **Real-time streaming workflow execution** — `GET /api/agents/stream/{event_id}` (SSE) runs the pipeline via LangGraph's `astream`, pushing one event per agent node as it completes so the dashboard can show live progress (~1–4s per LLM-backed agent, instant for the deterministic Decision Engine).
- **Synchronous workflow execution** — `POST /api/agents/run/{event_id}` for non-streaming clients, using `ainvoke`.
- **Full persistence** — every workflow run writes a `WorkflowRun` row (raw JSONB output per agent) and a `Report` row (executive/technical summaries + financials) to PostgreSQL.
- **PDF report export** — `GET /api/reports/{event_id}/pdf` renders a structured ReportLab PDF combining the `Report` summary with the full per-agent `WorkflowRun` output (observation, investigation, prediction, strategies, decision).
- **Live notification bell** — polls for unresolved `HIGH`/`CRITICAL` events every 30s and surfaces them in a dropdown with a badge count.
- **Theme support** — persisted dark/light mode toggle (localStorage-backed, applied pre-hydration to avoid flicker).
- **Password visibility toggle** on the login form.
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

To enable real AI-generated agent output (recommended), set your Anthropic API key in `backend/.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
```

If this is left empty, all six agents fall back to deterministic mock output — the pipeline still runs end-to-end and the UI still works, just with templated text.

Start local infrastructure:

```bash
docker compose up -d
docker compose ps
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

- Frontend (Lovable Vite): `http://localhost:8080` (or `5173`, depending on config)
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

### Daily startup (after first-time setup)

Terminal 1 — Backend:

```bash
cd backend
docker compose up -d
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Terminal 2 — Frontend:

```bash
cd frontend/athena-ai-dashboard-main
npm run dev
```

### Shutdown

```bash
# Ctrl+C in both terminals first
cd backend
docker compose down
```

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

1. Register or login (in development mode, new accounts are auto-elevated to `ADMIN`).
2. Open the protected dashboard.
3. Create, list, view, edit, and delete events.
4. Click "Run AI Core" on an event to stream the live multi-agent workflow.
5. Watch each of the 6 agent cards complete in real time as Claude generates observations, root-cause analysis, financial predictions, mitigation strategies, the decision, and the final report.
6. Download a structured PDF report from the Reports page.
7. Logout from the topbar or settings page.

The frontend self-register flow requests a `MANAGER` demo role so event creation, deletion, and workflow execution work end-to-end in local hackathon/demo environments. Backend RBAC still enforces role requirements on every endpoint. **In development mode (`ATHENA_ENV=development`, the default), the role is automatically elevated to `ADMIN` regardless of what is requested**, so local developers can immediately access every endpoint.

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
- Agent pipeline finishes instantly (under ~1 second) with templated-looking text: `ANTHROPIC_API_KEY` is missing, not loaded from `backend/.env`, or the API call is failing silently — agents are using the deterministic mock fallback. Check the backend logs for `ANTHROPIC_API_KEY not set — using fallback agent output` or `Claude API call failed — using fallback agent output`.

## API Endpoints

### Health

- `GET /healthz` — process health check.
- `GET /readyz` — dependency readiness placeholder.
- `GET /health/db` — PostgreSQL connectivity check with round-trip latency.

### Auth (`/api/auth`)

- `POST /api/auth/register` — create an account, returns token pair + user. In development mode, the assigned role is automatically elevated to `ADMIN`.
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

- `POST /api/agents/run/{event_id}` — run the full multi-agent pipeline synchronously (requires `ANALYST` or above). Uses `workflow.ainvoke()`.
- `GET /api/agents/stream/{event_id}?token=<access_token>` — run the pipeline and stream progress via Server-Sent Events (requires `ANALYST` or above). Uses `workflow.astream()`. Emits `started`, `node_complete` (×6), `done`, and `error` event types, followed by a `: stream-end` comment to close the connection cleanly.

**Example synchronous request:**

```bash
curl -X POST http://localhost:8000/api/agents/run/<event_id> \
  -H "Authorization: Bearer <access_token>"
```

**Example response structure:**

```json
{
  "event_id": "...",
  "event_status": "RESOLVED",
  "observation":   { "summary": "...", "detected_type": "...", "priority": "...", "risk_indicators": [], "confidence": 0.87 },
  "investigation": { "root_cause": "...", "impact": "...", "evidence": [], "confidence": 0.89 },
  "prediction":    { "revenue_risk": 12500.0, "delay_probability": 0.23, "churn_probability": 0.15, "severity_score": 6.8, "confidence": 0.85 },
  "strategies":    [ { "title": "...", "description": "...", "estimated_savings": 11000.0, "effort": "LOW", "risk_reduction": 0.85, "confidence": 0.92 } ],
  "decision":      { "selected_action": {}, "decision_reason": "...", "expected_savings": 11000.0, "confidence": 0.92, "requires_human_approval": false },
  "report":        { "executive_summary": "...", "technical_summary": "...", "recommended_action": "...", "estimated_savings": 11000.0, "confidence": 0.882 },
  "confidence_score": 0.882,
  "started_at": "2026-06-12T10:15:00Z",
  "completed_at": "2026-06-12T10:15:08Z",
  "errors": []
}
```

The workflow:
1. Fetches the event (404 if missing).
2. Sets status → `IN_PROGRESS`, records `WORKFLOW_STARTED` activity.
3. Runs 6 LangGraph agents in sequence (Observer, Investigation, Prediction, Strategy, Decision, Reporting). Observer, Investigation, Prediction, Strategy, and Reporting call the Claude API; Decision is a deterministic scoring function.
4. Persists a `WorkflowRun` row (raw per-agent JSONB output) and a `Report` row (summaries + financials).
5. On success: status → `RESOLVED`, records `WORKFLOW_COMPLETED`.
6. On failure: status → `FAILED`, records `WORKFLOW_FAILED`, session is rolled back cleanly.

`requires_human_approval` is `true` when severity is `CRITICAL`, decision confidence < 0.75, or expected savings > $500k.

### Reports (`/api/reports`)

- `GET /api/reports/{event_id}/pdf` — generate and download a structured PDF report (requires `VIEWER` or above). Combines the latest `Report` record (executive/technical summaries, estimated savings, confidence) with the latest `WorkflowRun` record (full per-agent pipeline output: observation, investigation, prediction, strategies, decision).

## Agent Pipeline Details

| Agent | Type | Output |
|---|---|---|
| Observer | LLM (Claude) | Summary, detected type, priority, risk indicators, confidence |
| Investigation | LLM (Claude) | Root cause, impact, evidence list, confidence |
| Prediction | LLM (Claude) | Revenue risk, delay/churn probability, severity score, confidence |
| Strategy | LLM (Claude) | 3 ranked mitigation options (title, description, savings, effort, risk reduction, confidence) |
| Decision | Deterministic | Scores each strategy (`savings + risk_reduction × 50,000 − effort_penalty`), selects the best, flags `requires_human_approval` |
| Reporting | LLM (Claude) | Executive summary, technical summary, recommended action |

Each LLM-backed agent calls `claude-sonnet-4-5-20250929` via the Anthropic API with a strict JSON-schema prompt. If `ANTHROPIC_API_KEY` is unset, the call fails, or the response can't be parsed as JSON, the agent falls back to deterministic mock output so the pipeline never breaks. The overall `confidence_score` (harmonic mean of all agent confidences) and `estimated_savings` are always computed deterministically, never taken from the LLM.

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
| `ATHENA_ENV` | `development` | When `development`, new registrations are auto-elevated to `ADMIN`. Set to `staging`/`production` to restore normal RBAC defaults. |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080` | Comma-separated allowed CORS origins for the frontend |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Legacy single-origin CORS variable (merged with `FRONTEND_ORIGINS`) |
| `JWT_SECRET_KEY` | *(must be set)* | HS256 signing secret, min 32 chars |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key used by the LLM-backed agent nodes. If empty, agents fall back to deterministic mock output. |
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

Core tables: `users`, `events`, `event_activities`, `workflow_runs`, `reports`, `refresh_tokens`, `audit_logs`.

`workflow_runs` stores one row per pipeline execution with the full JSONB output of every agent (`observation`, `investigation`, `prediction`, `strategies`, `decision`), overall confidence, status, errors, and timing. `reports` stores the final executive/technical summaries, recommended action, estimated savings, and confidence for each run.

## Testing Status

- Backend: `pytest` covers `/healthz`, `/health/db`, Alembic migrations, FK/unique constraints, ORM relationships, soft-delete filtering, full auth flow, event CRUD/pagination/filtering/RBAC, frontend integration contracts, and the LangGraph workflow endpoints (both synchronous and streaming).
- Frontend: `npm run build` passes; `npm run lint` passes with shadcn fast-refresh warnings only.
- LangGraph workflow integration tests: added for success, auth/RBAC, missing events, status transitions, activities, response sections, decision selection, confidence, and critical-event approval.
- Manually verified end-to-end: real-time SSE streaming with live Claude-generated agent output, PostgreSQL persistence (`workflow_runs` + `reports`), and PDF export reflecting the full pipeline.

## Roles

| Role | Description |
|---|---|
| `ADMIN` | Full platform access |
| `MANAGER` | Manage events and workflows |
| `ANALYST` | Create and update events and investigations |
| `VIEWER` | Read-only access |

## Known Limitations / Next Steps

- Agents reason from a single serialized event record, not live telemetry, logs, or system state — analysis quality depends entirely on the richness of the event payload at creation time. Connecting the Observer/Investigator agents to real data sources (SIEM, APM, ticketing) via tool-calling would ground their output in actual evidence.
- `ATHENA_ENV=development` auto-elevates every new registration to `ADMIN` — this must be changed to `staging`/`production` before any non-local deployment, or RBAC is effectively disabled.
- The notification bell currently polls `/api/events` for unresolved high/critical events on a 30s interval; a dedicated notifications table/websocket would be more efficient at scale.
- No automated tests yet for the Claude-backed agent fallback paths or the PDF pipeline-output formatting.