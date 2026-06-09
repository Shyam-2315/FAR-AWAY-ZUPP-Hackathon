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


def _register_user(client: TestClient, *, role: str = "ADMIN") -> dict[str, Any]:
    resp = client.post(
        "/api/auth/register",
        json={
            "name": f"Events {role}",
            "email": f"events_{role.lower()}_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password1",
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Port congestion risk",
        "description": "Inbound shipments are delayed at the west coast port.",
        "event_type": "logistics",
        "severity": "HIGH",
        "status": "NEW",
        "source": "erp",
        "tenant_id": "tenant-a",
        "metadata": {"region": "west"},
    }
    base.update(overrides)
    return base


def _create_event(client: TestClient, token: str, **overrides: Any) -> dict[str, Any]:
    resp = client.post("/api/events", json=_payload(**overrides), headers=_auth_headers(token))
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


def test_event_crud_flow(client: TestClient) -> None:
    data = _register_user(client, role="ADMIN")
    token = data["access_token"]

    created = _create_event(client, token)
    assert created["title"] == "Port congestion risk"
    assert created["metadata"] == {"region": "west"}
    assert created["timeline"][0]["activity_type"] == "CREATED"

    event_id = created["id"]
    fetched = client.get(f"/api/events/{event_id}", headers=_auth_headers(token))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == event_id

    patched = client.patch(
        f"/api/events/{event_id}",
        json={"status": "IN_PROGRESS", "severity": "CRITICAL"},
        headers=_auth_headers(token),
    )
    assert patched.status_code == 200, patched.text
    patched_body = patched.json()
    assert patched_body["status"] == "IN_PROGRESS"
    assert patched_body["severity"] == "CRITICAL"
    assert [item["activity_type"] for item in patched_body["timeline"]] == ["CREATED", "UPDATED"]

    deleted = client.delete(f"/api/events/{event_id}", headers=_auth_headers(token))
    assert deleted.status_code == 204

    missing = client.get(f"/api/events/{event_id}", headers=_auth_headers(token))
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "EVENT_NOT_FOUND"


def test_event_list_pagination_and_dashboard_shape(client: TestClient) -> None:
    token = _register_user(client, role="ADMIN")["access_token"]
    for index in range(3):
        _create_event(client, token, title=f"Paged event {index}", event_type="ops")

    resp = client.get(
        "/api/events?page=1&page_size=2&sort_by=title&sort_order=asc",
        headers=_auth_headers(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"items", "total", "page", "page_size"}
    assert body["total"] >= 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


def test_event_routes_require_auth(client: TestClient) -> None:
    resp = client.get("/api/events")
    assert resp.status_code in (401, 403)

    resp = client.post("/api/events", json=_payload())
    assert resp.status_code in (401, 403)


def test_event_create_requires_analyst_role(client: TestClient) -> None:
    token = _register_user(client, role="VIEWER")["access_token"]

    resp = client.post("/api/events", json=_payload(), headers=_auth_headers(token))

    assert resp.status_code == 403


def test_event_invalid_payload_returns_422(client: TestClient) -> None:
    token = _register_user(client, role="ADMIN")["access_token"]

    resp = client.post(
        "/api/events",
        json=_payload(title="", severity="BLOCKER"),
        headers=_auth_headers(token),
    )

    assert resp.status_code == 422


def test_event_update_rejects_read_only_fields(client: TestClient) -> None:
    token = _register_user(client, role="ADMIN")["access_token"]
    event = _create_event(client, token)

    resp = client.patch(
        f"/api/events/{event['id']}",
        json={"id": event["id"], "status": "IN_PROGRESS"},
        headers=_auth_headers(token),
    )

    assert resp.status_code == 422


def test_event_filtering_search_and_sorting(client: TestClient) -> None:
    token = _register_user(client, role="ADMIN")["access_token"]
    tenant_id = f"tenant-filter-{uuid.uuid4().hex[:8]}"
    _create_event(
        client,
        token,
        title="Checkout incident",
        event_type="payments",
        severity="LOW",
        status="RESOLVED",
        tenant_id="tenant-a",
    )
    _create_event(
        client,
        token,
        title="Warehouse delay",
        event_type="logistics",
        severity="CRITICAL",
        status="NEW",
        tenant_id=tenant_id,
    )

    resp = client.get(
        "/api/events?severity=CRITICAL&event_type=logistics&status=NEW&search=warehouse"
        f"&tenant_id={tenant_id}&sort_by=created_at&sort_order=desc",
        headers=_auth_headers(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Warehouse delay"
    assert body["items"][0]["severity"] == "CRITICAL"
    assert body["items"][0]["event_type"] == "logistics"
