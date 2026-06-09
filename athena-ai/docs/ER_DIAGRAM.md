# Entity-Relationship Diagram

Athena AI decision-intelligence schema. `User` and `Event` support soft delete via `deleted_at`.

## Mermaid ER Diagram

```mermaid
erDiagram
    users ||--o{ events : creates
    events ||--o{ investigations : has
    events ||--o{ predictions : has
    events ||--o{ recommendations : has
    events ||--o{ decisions : has
    events ||--o{ reports : has

    users {
        uuid id PK
        varchar name
        varchar email UK
        varchar password_hash
        user_role role
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    events {
        uuid id PK
        varchar title
        text description
        varchar event_type
        event_severity severity
        event_status status
        varchar source
        jsonb metadata
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    investigations {
        uuid id PK
        uuid event_id FK
        text root_cause
        text impact
        jsonb evidence
        float confidence
        timestamptz created_at
    }

    predictions {
        uuid id PK
        uuid event_id FK
        float revenue_risk
        float delay_probability
        float churn_probability
        float severity_score
        float confidence
        timestamptz created_at
    }

    recommendations {
        uuid id PK
        uuid event_id FK
        varchar title
        text description
        float estimated_savings
        effort_level effort
        float risk_reduction
        float confidence
        timestamptz created_at
    }

    decisions {
        uuid id PK
        uuid event_id FK
        jsonb selected_action
        text decision_reason
        float expected_savings
        float confidence
        boolean requires_human_approval
        timestamptz created_at
    }

    reports {
        uuid id PK
        uuid event_id FK
        varchar report_type
        text report_text
        float confidence
        timestamptz created_at
    }
```

## Cardinality

| Relationship | Cardinality | On delete |
| --- | --- | --- |
| `users` → `events` | 1:N | `RESTRICT` (cannot delete user with events) |
| `events` → `investigations` | 1:N | `CASCADE` |
| `events` → `predictions` | 1:N | `CASCADE` |
| `events` → `recommendations` | 1:N | `CASCADE` |
| `events` → `decisions` | 1:N | `CASCADE` |
| `events` → `reports` | 1:N | `CASCADE` |

## Enum Types

| PostgreSQL type | Values |
| --- | --- |
| `user_role` | `ADMIN`, `MANAGER`, `ANALYST`, `VIEWER` |
| `event_severity` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `event_status` | `NEW`, `IN_PROGRESS`, `RESOLVED`, `FAILED` |
| `effort_level` | `LOW`, `MEDIUM`, `HIGH` |

## Index Summary

| Table | Index | Purpose |
| --- | --- | --- |
| `users` | `ix_users_email` | Email lookups |
| `users` | `ix_users_email_active` (partial unique) | Active-email uniqueness with soft delete |
| `events` | `ix_events_status` | Status filtering |
| `events` | `ix_events_severity` | Severity filtering |
| `events` | `ix_events_created_by` | Creator lookups |
| `events` | `ix_events_created_at` | Chronological queries |
| `investigations` | `ix_investigations_event_id` | Event-scoped reads |
| `predictions` | `ix_predictions_event_id` | Event-scoped reads |
| `recommendations` | `ix_recommendations_event_id` | Event-scoped reads |
| `decisions` | `ix_decisions_event_id` | Event-scoped reads |
| `reports` | `ix_reports_event_id` | Event-scoped reads |
