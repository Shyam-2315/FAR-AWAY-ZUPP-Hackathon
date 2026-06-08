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
