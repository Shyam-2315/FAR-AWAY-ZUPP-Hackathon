"""
Phase 3.1 agent workflow test suite.

Covers:
  1. Successful workflow run returns 200 with all output sections.
  2. Missing event returns 404.
  3. Unauthenticated request is blocked (401/403).
  4. VIEWER role is blocked (403).
  5. ANALYST role can run the workflow.
  6. Event status becomes RESOLVED after a successful run.
  7. Event activities include WORKFLOW_STARTED and WORKFLOW_COMPLETED.
  8. Workflow response contains observation, investigation, prediction,
     strategies, decision, and report.
  9. Decision engine selects the highest-scoring strategy.
 10. Reporting agent sets a positive confidence_score.
 11. requires_human_approval is True for CRITICAL severity events.
"""

import sys
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.db.session import reset_engine_state
from app.main import create_app

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ------------------------------------------------------------------ #
# Fixtures and helpers
# ------------------------------------------------------------------ #


@pytest.fixture
def client() -> TestClient:
    reset_engine_state()
    app = create_app()
    test_settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-pytest-32chars!",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app, raise_server_exceptions=True)


def _register(client: TestClient, *, role: str = "ANALYST") -> dict[str, Any]:
    resp = client.post(
        "/api/auth/register",
        json={
            "name": f"WF {role}",
            "email": f"wf_{role.lower()}_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password1",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_event(
    client: TestClient,
    token: str,
    *,
    severity: str = "HIGH",
) -> dict[str, Any]:
    resp = client.post(
        "/api/events",
        json={
            "title": "Supply chain disruption",
            "description": "Upstream supplier has halted production.",
            "event_type": "supply_chain",
            "severity": severity,
            "source": "erp",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


# ------------------------------------------------------------------ #
# Test 1 — Successful workflow run
# ------------------------------------------------------------------ #


def test_workflow_run_returns_200(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)
    event_id = event["id"]

    resp = client.post(f"/api/agents/run/{event_id}", headers=_auth(token))

    assert resp.status_code == 200, resp.text


# ------------------------------------------------------------------ #
# Test 2 — Missing event returns 404
# ------------------------------------------------------------------ #


def test_workflow_missing_event_returns_404(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    fake_id = str(uuid.uuid4())

    resp = client.post(f"/api/agents/run/{fake_id}", headers=_auth(token))

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "EVENT_NOT_FOUND"


# ------------------------------------------------------------------ #
# Test 3 — Unauthenticated request is blocked
# ------------------------------------------------------------------ #


def test_workflow_requires_auth(client: TestClient) -> None:
    resp = client.post(f"/api/agents/run/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


# ------------------------------------------------------------------ #
# Test 4 — VIEWER role is blocked
# ------------------------------------------------------------------ #


def test_workflow_viewer_role_blocked(client: TestClient) -> None:
    # Create the event with an ADMIN so it exists.
    admin_token = _register(client, role="ADMIN")["access_token"]
    event = _create_event(client, admin_token)
    event_id = event["id"]

    viewer_token = _register(client, role="VIEWER")["access_token"]
    resp = client.post(f"/api/agents/run/{event_id}", headers=_auth(viewer_token))

    assert resp.status_code == 403


# ------------------------------------------------------------------ #
# Test 5 — ANALYST role can run workflow
# ------------------------------------------------------------------ #


def test_workflow_analyst_role_allowed(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))

    assert resp.status_code == 200


# ------------------------------------------------------------------ #
# Test 6 — Event status is RESOLVED after success
# ------------------------------------------------------------------ #


def test_workflow_event_status_resolved_after_success(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)
    event_id = event["id"]

    client.post(f"/api/agents/run/{event_id}", headers=_auth(token))

    # Fetch the event and check status.
    fetched = client.get(f"/api/events/{event_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "RESOLVED"


# ------------------------------------------------------------------ #
# Test 7 — Activities include WORKFLOW_STARTED and WORKFLOW_COMPLETED
# ------------------------------------------------------------------ #


def test_workflow_activities_recorded(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)
    event_id = event["id"]

    client.post(f"/api/agents/run/{event_id}", headers=_auth(token))

    fetched = client.get(f"/api/events/{event_id}", headers=_auth(token))
    timeline = fetched.json()["timeline"]
    activity_types = [item["activity_type"] for item in timeline]

    assert "WORKFLOW_STARTED" in activity_types
    assert "WORKFLOW_COMPLETED" in activity_types


# ------------------------------------------------------------------ #
# Test 8 — Response includes all required sections
# ------------------------------------------------------------------ #


def test_workflow_response_has_all_sections(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    body: dict[str, Any] = resp.json()

    assert "observation" in body
    assert "investigation" in body
    assert "prediction" in body
    assert "strategies" in body
    assert "decision" in body
    assert "report" in body
    assert "confidence_score" in body
    assert "started_at" in body
    assert "completed_at" in body
    assert "errors" in body


# ------------------------------------------------------------------ #
# Test 9 — Decision engine selects highest-scoring strategy
# ------------------------------------------------------------------ #


def test_workflow_decision_selects_best_strategy(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    body: dict[str, Any] = resp.json()

    decision = body["decision"]
    # "Reroute affected operation" has score = 85000 + 0.65*50000 - 25000 = 92500
    # "Notify impacted customers"  has score = 30000 + 0.30*50000 - 10000 = 35000
    # "Allocate backup resources"  has score = 60000 + 0.55*50000 - 50000 = 37500
    # Reroute should win.
    assert decision["selected_action"]["title"] == "Reroute affected operation"
    assert decision["expected_savings"] == 85_000.0


# ------------------------------------------------------------------ #
# Test 10 — Reporting agent sets confidence_score > 0
# ------------------------------------------------------------------ #


def test_workflow_confidence_score_positive(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    body: dict[str, Any] = resp.json()

    assert body["confidence_score"] > 0.0
    assert body["report"]["confidence"] > 0.0


# ------------------------------------------------------------------ #
# Test 11 — requires_human_approval True for CRITICAL severity
# ------------------------------------------------------------------ #


def test_workflow_critical_event_requires_approval(client: TestClient) -> None:
    # Need ADMIN to register, then ANALYST can create events too.
    token = _register(client, role="ADMIN")["access_token"]
    event = _create_event(client, token, severity="CRITICAL")

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    body: dict[str, Any] = resp.json()

    assert body["decision"]["requires_human_approval"] is True


# ------------------------------------------------------------------ #
# Test 12 — Response shape validation
# ------------------------------------------------------------------ #


def test_workflow_observation_shape(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    obs = resp.json()["observation"]

    assert obs["summary"] == "Operational event detected"
    assert obs["detected_type"] == "supply_chain"
    assert obs["priority"] == "HIGH"
    assert isinstance(obs["risk_indicators"], list)
    assert obs["confidence"] == 0.85


def test_workflow_investigation_shape(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    inv = resp.json()["investigation"]

    assert "root_cause" in inv
    assert "impact" in inv
    assert isinstance(inv["evidence"], list)
    assert inv["confidence"] == 0.80


def test_workflow_prediction_shape(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    pred = resp.json()["prediction"]

    assert pred["revenue_risk"] == 125_000.0
    assert pred["delay_probability"] == 0.72
    assert pred["churn_probability"] == 0.18
    assert pred["severity_score"] == 7.5
    assert pred["confidence"] == 0.78


def test_workflow_strategies_shape(client: TestClient) -> None:
    token = _register(client, role="ANALYST")["access_token"]
    event = _create_event(client, token)

    resp = client.post(f"/api/agents/run/{event['id']}", headers=_auth(token))
    strategies = resp.json()["strategies"]

    assert len(strategies) == 3
    for s in strategies:
        assert "title" in s
        assert "description" in s
        assert "estimated_savings" in s
        assert "effort" in s
        assert s["effort"] in ("LOW", "MEDIUM", "HIGH")
        assert "risk_reduction" in s
        assert "confidence" in s
