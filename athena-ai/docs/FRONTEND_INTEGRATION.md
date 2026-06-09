# Frontend Integration Guide

This document is the single source of truth for connecting a Lovable.dev (React/Vite/Next.js) frontend to the Athena AI backend.

---

## Backend Base URL

| Environment | URL |
|---|---|
| Local development | `http://localhost:8000` |
| Staging / Production | Set via `VITE_API_BASE_URL` or `NEXT_PUBLIC_API_BASE_URL` |

The interactive Swagger UI is available at `http://localhost:8000/docs` when the backend is running locally.

---

## Frontend Environment Variables

Create a `.env.local` file in the frontend project root:

**For Vite (Lovable.dev default):**

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

**For Next.js:**

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Reference it in code:

```ts
// Vite
const API = import.meta.env.VITE_API_BASE_URL;

// Next.js
const API = process.env.NEXT_PUBLIC_API_BASE_URL;
```

---

## CORS Setup

The backend accepts requests from the following origins by default when running locally:

- `http://localhost:3000` (Next.js / CRA)
- `http://localhost:5173` (Vite — Lovable.dev default)
- `http://localhost:8080` (alternate dev port)

These are controlled by two environment variables on the **backend** `.env`:

```dotenv
# Any of these may be set — both are merged and deduplicated
BACKEND_CORS_ORIGINS=http://localhost:3000
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
```

To add a staging or Lovable.dev preview URL:

```dotenv
FRONTEND_ORIGINS=http://localhost:5173,https://your-app.lovable.app
```

The wildcard `"*"` is never used — credentials (`Authorization` header, cookies) require explicit origins.

---

## Required Headers

Every authenticated request must include:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Auth Endpoints

### Register

```
POST /api/auth/register
```

**Request body:**

```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "password": "SecurePass1",
  "role": "VIEWER"
}
```

- `role` is optional (defaults to `"VIEWER"`). Allowed values: `ADMIN`, `MANAGER`, `ANALYST`, `VIEWER`.
- `password` must be ≥ 8 characters and contain at least one letter and one digit.

**Response `201`:**

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "a7b3c2...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Alice",
    "email": "alice@example.com",
    "role": "VIEWER",
    "is_active": true,
    "created_at": "2025-06-08T12:00:00Z"
  }
}
```

---

### Login

```
POST /api/auth/login
```

**Request body:**

```json
{
  "email": "alice@example.com",
  "password": "SecurePass1"
}
```

**Response `200`:** Same envelope as register.

**Error `401`:**

```json
{ "detail": "Invalid email or password" }
```

---

### Refresh Token

```
POST /api/auth/refresh
```

Call this when the access token is about to expire (or after receiving a 401). The old refresh token is revoked and a new pair is issued.

**Request body:**

```json
{
  "refresh_token": "a7b3c2..."
}
```

**Response `200`:** Same envelope as login — store the **new** refresh token and discard the old one.

**Error `401`:** Token is invalid, expired, or already revoked.

---

### Logout

```
POST /api/auth/logout
Authorization: Bearer <access_token>
```

**Request body:**

```json
{
  "refresh_token": "a7b3c2..."
}
```

**Response `204 No Content`** — no body.

After receiving 204, clear both tokens from local storage.

---

### Current User

```
GET /api/auth/me
Authorization: Bearer <access_token>
```

**Response `200`:**

```json
{
  "user": {
    "id": "550e8400-...",
    "name": "Alice",
    "email": "alice@example.com",
    "role": "VIEWER",
    "is_active": true,
    "created_at": "2025-06-08T12:00:00Z"
  }
}
```

---

## Event Endpoints

### Create Event

```
POST /api/events
Authorization: Bearer <access_token>
```

Requires `ANALYST` role or above.

**Request body:**

```json
{
  "title": "Port congestion risk",
  "description": "Inbound shipments delayed at west coast port.",
  "event_type": "logistics",
  "severity": "HIGH",
  "status": "NEW",
  "source": "erp",
  "tenant_id": "tenant-a",
  "metadata": { "region": "west" }
}
```

- `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `status`: `NEW`, `IN_PROGRESS`, `RESOLVED`, `FAILED` (default `NEW`)
- `tenant_id`, `description`, `metadata` are optional

**Response `201`:**

```json
{
  "id": "...",
  "title": "Port congestion risk",
  "description": "...",
  "event_type": "logistics",
  "severity": "HIGH",
  "status": "NEW",
  "source": "erp",
  "tenant_id": "tenant-a",
  "metadata": { "region": "west" },
  "created_by": "<user-uuid>",
  "created_at": "2025-06-08T12:00:00Z",
  "updated_at": "2025-06-08T12:00:00Z",
  "timeline": [
    {
      "id": "...",
      "event_id": "...",
      "activity_type": "CREATED",
      "actor_id": "<user-uuid>",
      "tenant_id": "tenant-a",
      "details": {},
      "created_at": "2025-06-08T12:00:00Z"
    }
  ]
}
```

---

### List Events

```
GET /api/events
Authorization: Bearer <access_token>
```

Requires `VIEWER` role or above.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | `1` | Page number (1-indexed) |
| `page_size` | int | `20` | Results per page (max 100) |
| `search` | string | — | Full-text search on title/description |
| `severity` | string | — | Filter by severity (repeatable) |
| `event_type` | string | — | Filter by event type (repeatable) |
| `status` | string | — | Filter by status (repeatable) |
| `tenant_id` | string | — | Filter by tenant |
| `sort_by` | string | `created_at` | `created_at`, `updated_at`, `severity`, `status`, `event_type`, `title` |
| `sort_order` | string | `desc` | `asc` or `desc` |

**Response `200`:**

```json
{
  "items": [ /* EventOut objects */ ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

### Get Single Event

```
GET /api/events/{event_id}
Authorization: Bearer <access_token>
```

**Response `200`:** Full `EventOut` object including `timeline`.

**Error `404`:**

```json
{ "detail": { "code": "EVENT_NOT_FOUND", "message": "Event not found" } }
```

---

### Update Event

```
PATCH /api/events/{event_id}
Authorization: Bearer <access_token>
```

Requires `ANALYST` role or above. Send only the fields you want to change.

**Request body (all fields optional):**

```json
{
  "status": "IN_PROGRESS",
  "severity": "CRITICAL"
}
```

**Response `200`:** Updated `EventOut` with new `timeline` entry.

---

### Delete Event

```
DELETE /api/events/{event_id}
Authorization: Bearer <access_token>
```

Requires `MANAGER` role or above. Soft-deletes the event (it is hidden from list results but not permanently removed from the database).

**Response `204 No Content`.**

---

## Refresh Token Flow (Frontend Pattern)

Recommended implementation using an Axios interceptor or equivalent:

```ts
// Pseudocode — adapt to your HTTP client
async function apiRequest(config) {
  try {
    return await http(config);
  } catch (err) {
    if (err.status === 401 && !config._retried) {
      const stored = getStoredRefreshToken();
      const resp = await http.post('/api/auth/refresh', { refresh_token: stored });
      setTokens(resp.data.access_token, resp.data.refresh_token);
      config._retried = true;
      config.headers.Authorization = `Bearer ${resp.data.access_token}`;
      return http(config);
    }
    throw err;
  }
}
```

Key rules:
- Store `access_token` in memory (a React context or Zustand store), not `localStorage`.
- Store `refresh_token` in an `httpOnly` cookie (preferred) or `localStorage` as a fallback.
- On 401 from refresh, redirect to login and clear all tokens.
- After a successful refresh, **replace** the stored refresh token with the new one — the old one is revoked.

---

## Error Response Format

All API errors return a consistent JSON body:

```json
{ "detail": "Human-readable message" }
```

For domain errors (e.g., event not found), the detail is an object:

```json
{ "detail": { "code": "EVENT_NOT_FOUND", "message": "Event not found" } }
```

Validation errors (`422`) return FastAPI's standard format:

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error" }
  ]
}
```

---

## Local Development Checklist

1. `docker compose up -d` — start PostgreSQL and Redis
2. `cd backend && alembic upgrade head` — apply migrations
3. `uvicorn app.main:app --reload` — start backend on `:8000`
4. `cd frontend && npm install && npm run dev` — start Vite frontend on `:5173`
5. Backend Swagger UI: `http://localhost:8000/docs`
6. Confirm CORS: open browser devtools on `:5173` and make a request to `:8000/healthz` — it should succeed without CORS errors
