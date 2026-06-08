# API Contracts

Base URL: `/api`

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create an account and return token pair plus user. |
| `POST` | `/api/auth/login` | Authenticate and return token pair plus user. |
| `POST` | `/api/auth/refresh` | Rotate refresh token and return a new token pair. |
| `POST` | `/api/auth/logout` | Revoke refresh token. |
| `GET` | `/api/auth/me` | Return current user. |

## Events

### Create Event

`POST /api/events`

Requires `ANALYST+`.

```json
{
  "title": "Port congestion risk",
  "description": "Inbound shipments are delayed.",
  "event_type": "logistics",
  "severity": "HIGH",
  "status": "NEW",
  "source": "erp",
  "tenant_id": "tenant-a",
  "metadata": {
    "region": "west"
  }
}
```

### List Events

`GET /api/events`

Requires `VIEWER+`.

Query parameters:

- `page`
- `page_size`
- `search`
- `severity`
- `event_type`
- `status`
- `tenant_id`
- `sort_by`
- `sort_order`

Response:

```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0000-000000000000",
      "title": "Port congestion risk",
      "description": "Inbound shipments are delayed.",
      "event_type": "logistics",
      "severity": "HIGH",
      "status": "NEW",
      "source": "erp",
      "tenant_id": "tenant-a",
      "metadata": {
        "region": "west"
      },
      "created_by": "00000000-0000-0000-0000-000000000000",
      "created_at": "2026-06-08T00:00:00Z",
      "updated_at": "2026-06-08T00:00:00Z",
      "timeline": []
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### Get Event

`GET /api/events/{event_id}`

Requires `VIEWER+`. Returns the same event item shape used in list responses, including `timeline`.

### Update Event

`PATCH /api/events/{event_id}`

Requires `ANALYST+`. All fields are optional.

```json
{
  "status": "PROCESSING",
  "severity": "CRITICAL"
}
```

### Delete Event

`DELETE /api/events/{event_id}`

Requires `MANAGER+`. Returns `204 No Content`.

## Agent Workflow (`/api/agents`)

### Run Workflow

`POST /api/agents/run/{event_id}`

Requires `ANALYST+`. Triggers the full multi-agent pipeline:
Observer → Investigation → Prediction → Strategy → Decision → Reporting.

**Path parameter:** `event_id` — UUID of an existing, non-deleted event.

**Response `200`:**

```json
{
  "event_id": "uuid",
  "event_status": "RESOLVED",
  "observation": {
    "summary": "Operational event detected",
    "detected_type": "logistics",
    "priority": "HIGH",
    "risk_indicators": [],
    "confidence": 0.85
  },
  "investigation": {
    "root_cause": "Initial root cause analysis generated from event context",
    "impact": "Potential operational delay and customer impact",
    "evidence": [],
    "confidence": 0.80
  },
  "prediction": {
    "revenue_risk": 125000.0,
    "delay_probability": 0.72,
    "churn_probability": 0.18,
    "severity_score": 7.5,
    "confidence": 0.78
  },
  "strategies": [
    {
      "title": "Reroute affected operation",
      "description": "...",
      "estimated_savings": 85000.0,
      "effort": "MEDIUM",
      "risk_reduction": 0.65,
      "confidence": 0.82
    }
  ],
  "decision": {
    "selected_action": { "title": "Reroute affected operation", "..." : "..." },
    "decision_reason": "Strategy 'Reroute affected operation' selected...",
    "expected_savings": 85000.0,
    "confidence": 0.82,
    "requires_human_approval": false
  },
  "report": {
    "executive_summary": "...",
    "technical_summary": "...",
    "recommended_action": "Reroute affected operation",
    "estimated_savings": 85000.0,
    "confidence": 0.81
  },
  "confidence_score": 0.81,
  "started_at": "2026-06-08T12:00:00Z",
  "completed_at": "2026-06-08T12:00:01Z",
  "errors": []
}
```

**`requires_human_approval` is `true` when:**
- Event severity is `CRITICAL`
- Decision confidence < 0.75
- Expected savings > $500,000

**Errors:**

| Status | Code | When |
|---|---|---|
| 401 | — | Missing or invalid Bearer token |
| 403 | — | Role below ANALYST |
| 404 | `EVENT_NOT_FOUND` | Event does not exist or is soft-deleted |
| 500 | `WORKFLOW_FAILED` | Pipeline raised an unhandled exception |
| 500 | `WORKFLOW_INCOMPLETE` | Pipeline completed but outputs are missing |

## Error Shape

Service errors use a structured detail object:

```json
{
  "detail": {
    "code": "EVENT_NOT_FOUND",
    "message": "Event 00000000-0000-0000-0000-000000000000 was not found"
  }
}
```

Validation errors use FastAPI's standard `422` response.
