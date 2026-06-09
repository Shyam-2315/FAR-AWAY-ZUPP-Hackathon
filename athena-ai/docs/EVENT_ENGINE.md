# Event Management Engine

The Event Management Engine exposes JWT-protected CRUD APIs for operational events and stores an immutable activity timeline for dashboard and workflow views.

## Architecture

- `app/api/events.py` keeps HTTP routing thin and delegates behavior to the service layer.
- `app/services/event_service.py` owns event lifecycle behavior, structured service errors, and timeline recording.
- `app/repositories/event_repository.py` owns SQLAlchemy queries for CRUD, pagination, filtering, sorting, search, and activity inserts.
- `app/schemas/events.py` defines Pydantic request and response contracts.
- `events.tenant_id` and `event_activities.tenant_id` keep the storage model tenant-ready without hard-coding a tenant provider into JWTs yet.

## Endpoints

| Method | Path | Role | Description |
|---|---|---|---|
| `POST` | `/api/events` | `ANALYST+` | Create an event and record `CREATED` activity. |
| `GET` | `/api/events` | `VIEWER+` | List events with pagination, filters, search, and sorting. |
| `GET` | `/api/events/{event_id}` | `VIEWER+` | Fetch one event with timeline. |
| `PATCH` | `/api/events/{event_id}` | `ANALYST+` | Update event fields and record `UPDATED` activity. |
| `DELETE` | `/api/events/{event_id}` | `MANAGER+` | Soft-delete an event. |

## List Contract

Responses use a Lovable.dev-compatible dashboard envelope:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

Supported query parameters:

| Parameter | Type | Notes |
|---|---|---|
| `page` | integer | 1-based page number. |
| `page_size` | integer | 1 to 100. |
| `search` | string | Searches title, description, event type, and source. |
| `severity` | repeated enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| `event_type` | repeated string | Exact event type filter. |
| `status` | repeated enum | `NEW`, `IN_PROGRESS`, `RESOLVED`, `FAILED`. |
| `tenant_id` | string | Exact tenant scope filter. |
| `sort_by` | enum | `created_at`, `updated_at`, `severity`, `status`, `event_type`, `title`. |
| `sort_order` | enum | `asc` or `desc`. |

Repeated filters use standard query repetition:

```text
/api/events?severity=HIGH&severity=CRITICAL&status=NEW
```

## Timeline

Each event can include `timeline`, ordered by `created_at`.

Activity types:

- `CREATED`
- `UPDATED`
- `WORKFLOW_STARTED`
- `WORKFLOW_COMPLETED`
- `WORKFLOW_FAILED`

The service exposes `record_workflow_activity` for workflow integrations. It records workflow activity and updates event status:

| Activity | Event status |
|---|---|
| `WORKFLOW_STARTED` | `IN_PROGRESS` |
| `WORKFLOW_COMPLETED` | `RESOLVED` |
| `WORKFLOW_FAILED` | `FAILED` |

## Security

- All event routes require Bearer JWT authentication.
- Reads allow `VIEWER` and above.
- Create/update require `ANALYST` and above.
- Delete requires `MANAGER` and above.
- Structured service errors use `detail.code` and `detail.message`, for example `EVENT_NOT_FOUND`.

## Database

Migration `20250608_0003_event_engine.py` adds:

- `events.tenant_id`
- `event_activities`
- `event_activity_type` enum
- indexes for event type, tenant, activity type, event ID, and activity timestamp
