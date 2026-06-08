"""
Frontend integration tests.

Verifies:
  - CORS origin parsing from FRONTEND_ORIGINS env variable
  - CORS origin deduplication when BACKEND_CORS_ORIGINS and FRONTEND_ORIGINS overlap
  - Auth login/register response shape matches the Lovable.dev envelope
  - Event list response shape matches the dashboard contract
  - CORS preflight request is handled correctly for allowed and blocked origins
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
# Fixtures
# ------------------------------------------------------------------ #


def _make_client(
    frontend_origins: str = "http://localhost:3000,http://localhost:5173",
    backend_cors_origins: str = "http://localhost:3000",
) -> TestClient:
    reset_engine_state()
    app = create_app()
    test_settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-pytest-32chars!",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        FRONTEND_ORIGINS=frontend_origins,
        BACKEND_CORS_ORIGINS=backend_cors_origins,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def client() -> TestClient:
    return _make_client()


def _register(client: TestClient, *, role: str = "ADMIN") -> dict[str, Any]:
    email = f"fi_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"name": "FI User", "email": email, "password": "Password1", "role": role},
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


# ------------------------------------------------------------------ #
# CORS config parsing
# ------------------------------------------------------------------ #


def test_settings_parses_frontend_origins_csv() -> None:
    settings = Settings(
        FRONTEND_ORIGINS="http://localhost:3000,http://localhost:5173,http://localhost:8080",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    origins = settings.backend_cors_origins
    assert "http://localhost:3000" in origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:8080" in origins


def test_settings_deduplicates_overlapping_origins() -> None:
    settings = Settings(
        FRONTEND_ORIGINS="http://localhost:3000,http://localhost:5173",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    origins = settings.backend_cors_origins
    # :3000 appears in both — should appear exactly once.
    assert origins.count("http://localhost:3000") == 1
    assert "http://localhost:5173" in origins


def test_settings_handles_whitespace_in_origins() -> None:
    settings = Settings(
        FRONTEND_ORIGINS=" http://localhost:3000 ,  http://localhost:5173  ",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    origins = settings.backend_cors_origins
    assert "http://localhost:3000" in origins
    assert "http://localhost:5173" in origins
    # No entries with surrounding spaces.
    assert all(o == o.strip() for o in origins)


def test_settings_handles_single_origin() -> None:
    settings = Settings(
        FRONTEND_ORIGINS="http://localhost:5173",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    origins = settings.backend_cors_origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_settings_preserves_insertion_order() -> None:
    """First unique occurrence of each origin should be preserved."""
    settings = Settings(
        FRONTEND_ORIGINS="http://app.example.com,http://localhost:5173",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    origins = settings.backend_cors_origins
    # BACKEND_CORS_ORIGINS is processed first, so :3000 comes first.
    assert origins[0] == "http://localhost:3000"


# ------------------------------------------------------------------ #
# CORS preflight
# ------------------------------------------------------------------ #


def test_cors_preflight_allowed_origin_returns_200(client: TestClient) -> None:
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    # FastAPI/Starlette returns 200 for CORS preflight on allowed origins.
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight_blocked_origin_has_no_allow_header(client: TestClient) -> None:
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Blocked origin — no allow-origin header in the response.
    assert "access-control-allow-origin" not in resp.headers


# ------------------------------------------------------------------ #
# Auth response shape (Lovable.dev envelope)
# ------------------------------------------------------------------ #


def test_register_response_has_lovable_envelope_shape(client: TestClient) -> None:
    data = _register(client)

    # Top-level token fields
    assert isinstance(data.get("access_token"), str)
    assert len(data["access_token"]) > 20
    assert isinstance(data.get("refresh_token"), str)
    assert len(data["refresh_token"]) > 20
    assert data.get("token_type") == "bearer"

    # Nested user object
    user = data.get("user")
    assert isinstance(user, dict)
    assert isinstance(user.get("id"), str)
    assert isinstance(user.get("name"), str)
    assert isinstance(user.get("email"), str)
    assert isinstance(user.get("role"), str)
    assert isinstance(user.get("is_active"), bool)
    assert isinstance(user.get("created_at"), str)  # ISO-8601 string over the wire


def test_login_response_has_lovable_envelope_shape(client: TestClient) -> None:
    data = _register(client)
    email = data["user"]["email"]

    resp = client.post("/api/auth/login", json={"email": email, "password": "Password1"})
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()

    assert set(body.keys()) >= {"access_token", "refresh_token", "token_type", "user"}
    user = body["user"]
    assert set(user.keys()) >= {"id", "name", "email", "role", "is_active", "created_at"}


def test_register_response_user_fields_are_correct_types(client: TestClient) -> None:
    data = _register(client, role="ANALYST")
    user = data["user"]

    assert user["role"] == "ANALYST"
    assert user["is_active"] is True
    # id should be a valid UUID string
    uuid.UUID(user["id"])


def test_me_response_has_user_object(client: TestClient) -> None:
    data = _register(client)
    token = data["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()
    assert "user" in body
    assert set(body["user"].keys()) >= {"id", "name", "email", "role", "is_active", "created_at"}


# ------------------------------------------------------------------ #
# Event list response shape (dashboard contract)
# ------------------------------------------------------------------ #


def test_event_list_response_has_pagination_envelope(client: TestClient) -> None:
    token = _register(client, role="ADMIN")["access_token"]

    resp = client.get("/api/events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body: dict[str, Any] = resp.json()

    # Exact top-level keys
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] >= 0
    assert isinstance(body["page"], int)
    assert isinstance(body["page_size"], int)


def test_event_list_default_page_values(client: TestClient) -> None:
    token = _register(client, role="ADMIN")["access_token"]

    resp = client.get("/api/events", headers={"Authorization": f"Bearer {token}"})
    body: dict[str, Any] = resp.json()

    assert body["page"] == 1
    assert body["page_size"] == 20


def test_event_list_item_shape(client: TestClient) -> None:
    token = _register(client, role="ADMIN")["access_token"]

    # Create one event so we have something to inspect.
    create_resp = client.post(
        "/api/events",
        json={
            "title": "Shape test event",
            "event_type": "test",
            "severity": "LOW",
            "source": "pytest",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201

    resp = client.get("/api/events?search=Shape+test", headers={"Authorization": f"Bearer {token}"})
    body: dict[str, Any] = resp.json()
    assert body["total"] >= 1
    item = body["items"][0]

    required_event_fields = {
        "id", "title", "event_type", "severity", "status",
        "source", "created_by", "created_at", "updated_at", "timeline",
    }
    assert required_event_fields.issubset(set(item.keys()))
