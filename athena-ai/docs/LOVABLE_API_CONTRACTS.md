# Lovable API Contracts

Machine-readable API contracts for the Lovable.dev frontend builder.

---

## API Base URL

```
http://localhost:8000
```

Set `VITE_API_BASE_URL=http://localhost:8000` in the frontend `.env.local`.

---

## Auth Header Format

All authenticated requests must include:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Endpoints

### POST /api/auth/register

Create a new user account. Returns token pair immediately — no separate login needed.

**Request:**

```json
{
  "name": "string (required, 1–255 chars)",
  "email": "string (required, valid email)",
  "password": "string (required, 8–128 chars, min 1 letter + 1 digit)",
  "role": "VIEWER | ANALYST | MANAGER | ADMIN  (optional, default VIEWER)"
}
```

**Response 201:**

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "string",
    "email": "string",
    "role": "VIEWER | ANALYST | MANAGER | ADMIN",
    "is_active": true,
    "created_at": "ISO-8601 datetime"
  }
}
```

**Errors:**

| Status | When |
|---|---|
| 409 | Email already registered |
| 422 | Validation failure (bad email, weak password, unknown role) |

---

### POST /api/auth/login

Exchange credentials for a token pair.

**Request:**

```json
{
  "email": "string",
  "password": "string"
}
```

**Response 200:** Same shape as `/register` 201.

**Errors:**

| Status | When |
|---|---|
| 401 | Invalid email or password, or account inactive |

---

### POST /api/auth/refresh

Rotate refresh token. Old token is revoked atomically; store the new refresh token and discard the old one.

**Request:**

```json
{
  "refresh_token": "string"
}
```

**Response 200:** Same shape as `/login` 200.

**Errors:**

| Status | When |
|---|---|
| 401 | Token invalid, expired, or already revoked |

---

### POST /api/auth/logout

Revoke the provided refresh token (single-device logout). Requires a valid Bearer access token.

**Request:**

```json
{
  "refresh_token": "string"
}
```

**Response 204:** No body.

**Errors:**

| Status | When |
|---|---|
| 400 | Refresh token not found or belongs to a different user |
| 401 | Missing or invalid Bearer token |

---

### GET /api/auth/me

Return the current user's profile.

**Request:** No body. Requires `Authorization: Bearer <token>`.

**Response 200:**

```json
{
  "user": {
    "id": "uuid",
    "name": "string",
    "email": "string",
    "role": "string",
    "is_active": true,
    "created_at": "ISO-8601 datetime"
  }
}
```

**Errors:**

| Status | When |
|---|---|
| 401 | Missing, invalid, or expired Bearer token |

---

### POST /api/events

Create an event. Requires `ANALYST` role or above.

**Request:**

```json
{
  "title": "string (required, 1–500 chars)",
  "description": "string | null (optional, max 10 000 chars)",
  "event_type": "string (required, 1–100 chars)",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "status": "NEW | IN_PROGRESS | RESOLVED | FAILED  (optional, default NEW)",
  "source": "string (required, 1–255 chars)",
  "tenant_id": "string | null (optional, 1–100 chars)",
  "metadata": "object (optional, default {})"
}
```

**Response 201:**

```json
{
  "id": "uuid",
  "title": "string",
  "description": "string | null",
  "event_type": "string",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "status": "NEW | IN_PROGRESS | RESOLVED | FAILED",
  "source": "string",
  "tenant_id": "string | null",
  "metadata": "object",
  "created_by": "uuid",
  "created_at": "ISO-8601 datetime",
  "updated_at": "ISO-8601 datetime",
  "timeline": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "activity_type": "CREATED | UPDATED | DELETED",
      "actor_id": "uuid | null",
      "tenant_id": "string | null",
      "details": "object",
      "created_at": "ISO-8601 datetime"
    }
  ]
}
```

**Errors:**

| Status | When |
|---|---|
| 403 | Role below ANALYST |
| 422 | Validation failure |

---

### GET /api/events

List events with pagination, filtering, and sorting. Requires `VIEWER` role or above.

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `page` | integer | `1` | 1-indexed |
| `page_size` | integer | `20` | 1–100 |
| `search` | string | — | Full-text search on title and description |
| `severity` | string | — | Repeatable: `?severity=HIGH&severity=CRITICAL` |
| `event_type` | string | — | Repeatable |
| `status` | string | — | Repeatable |
| `tenant_id` | string | — | Exact match |
| `sort_by` | string | `created_at` | `created_at` `updated_at` `severity` `status` `event_type` `title` |
| `sort_order` | string | `desc` | `asc` or `desc` |

**Response 200:**

```json
{
  "items": [ /* array of EventOut — see POST /api/events response shape */ ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**Errors:**

| Status | When |
|---|---|
| 401 | Missing or invalid Bearer token |
| 403 | Role below VIEWER |

---

### GET /api/events/{event_id}

Fetch a single event by UUID.

**Response 200:** Full EventOut object (same as create response).

**Errors:**

| Status | When |
|---|---|
| 404 | `{ "detail": { "code": "EVENT_NOT_FOUND", "message": "..." } }` |

---

### PATCH /api/events/{event_id}

Partial update. Send only the fields to change. Requires `ANALYST` role or above.

**Request (all fields optional):**

```json
{
  "title": "string | null",
  "description": "string | null",
  "event_type": "string | null",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL | null",
  "status": "NEW | IN_PROGRESS | RESOLVED | FAILED | null",
  "source": "string | null",
  "tenant_id": "string | null",
  "metadata": "object | null"
}
```

**Response 200:** Updated EventOut with a new `UPDATED` entry in `timeline`.

---

### DELETE /api/events/{event_id}

Soft-delete an event. Requires `MANAGER` role or above.

**Response 204:** No body.

**Errors:**

| Status | When |
|---|---|
| 403 | Role below MANAGER |
| 404 | Event not found |

---

## Error Format Reference

### Generic error

```json
{ "detail": "Human-readable message" }
```

### Domain error (structured)

```json
{ "detail": { "code": "EVENT_NOT_FOUND", "message": "Event not found" } }
```

### Validation error (422)

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

---

## TypeScript Type Sketches

```ts
// Auth
interface User {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'MANAGER' | 'ANALYST' | 'VIEWER';
  is_active: boolean;
  created_at: string; // ISO-8601
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: User;
}

// Events
type EventSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
type EventStatus = 'NEW' | 'IN_PROGRESS' | 'RESOLVED' | 'FAILED';
type ActivityType = 'CREATED' | 'UPDATED' | 'DELETED';

interface EventActivity {
  id: string;
  event_id: string;
  activity_type: ActivityType;
  actor_id: string | null;
  tenant_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

interface EventOut {
  id: string;
  title: string;
  description: string | null;
  event_type: string;
  severity: EventSeverity;
  status: EventStatus;
  source: string;
  tenant_id: string | null;
  metadata: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
  timeline: EventActivity[];
}

interface EventListOut {
  items: EventOut[];
  total: number;
  page: number;
  page_size: number;
}
```
