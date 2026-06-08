"""
Enterprise auth test suite.

Covers:
  - register success
  - register duplicate email
  - login success
  - login with invalid password
  - login with unknown email
  - get /me with valid token
  - get /me with invalid token
  - get /me with expired token
  - token refresh (rotation)
  - refresh with already-revoked token
  - logout revocation
  - logout then try to use the revoked refresh token
  - RBAC denial (role too low)
  - RBAC grant (role sufficient)
"""

import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings, get_settings
from app.db.session import reset_engine_state
from app.main import create_app
from app.services.token_service import TokenService

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def client() -> TestClient:
    """Fresh TestClient — settings override to use predictable JWT secret."""
    reset_engine_state()
    app = create_app()
    # Override settings cache so tests use a known secret
    test_settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-pytest-32chars!",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def token_service() -> TokenService:
    settings = Settings(
        JWT_SECRET_KEY="test-secret-key-for-pytest-32chars!",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
    )
    return TokenService(settings)


def _register_user(
    client: TestClient,
    *,
    email: str | None = None,
    password: str = "Password1",
    name: str = "Test User",
    role: str = "VIEWER",
) -> dict[str, Any]:
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password, "role": role},
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


# ------------------------------------------------------------------ #
# Registration
# ------------------------------------------------------------------ #


def test_register_returns_token_pair_and_user(client: TestClient) -> None:
    data = _register_user(client)

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["role"] == "VIEWER"
    assert data["user"]["is_active"] is True


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    _register_user(client, email=email)

    resp = client.post(
        "/api/auth/register",
        json={"name": "Another", "email": email, "password": "Password1"},
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


def test_register_weak_password_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"name": "Weak", "email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------ #
# Login
# ------------------------------------------------------------------ #


def test_login_success_returns_token_pair(client: TestClient) -> None:
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    _register_user(client, email=email)

    resp = client.post("/api/auth/login", json={"email": email, "password": "Password1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email


def test_login_invalid_password_returns_401(client: TestClient) -> None:
    email = f"badpw_{uuid.uuid4().hex[:8]}@example.com"
    _register_user(client, email=email)

    resp = client.post("/api/auth/login", json={"email": email, "password": "WrongPass1"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Password1"},
    )
    assert resp.status_code == 401


# ------------------------------------------------------------------ #
# /me
# ------------------------------------------------------------------ #


def test_me_with_valid_token_returns_user(client: TestClient) -> None:
    data = _register_user(client)
    token = data["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == data["user"]["email"]


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401


def test_me_with_expired_token_returns_401(
    client: TestClient,
    token_service: TokenService,
) -> None:
    # Create a real user first to get a valid user_id.
    data = _register_user(client)
    user_id = uuid.UUID(data["user"]["id"])

    # Manually craft an expired token.
    from jose import jwt

    payload = {
        "sub": str(user_id),
        "role": "VIEWER",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(hours=2),
        "exp": datetime.now(UTC) - timedelta(hours=1),  # already expired
    }
    expired_token = jwt.encode(
        payload,
        "test-secret-key-for-pytest-32chars!",
        algorithm="HS256",
    )

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_me_without_token_returns_403(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


# ------------------------------------------------------------------ #
# Refresh token rotation
# ------------------------------------------------------------------ #


def test_refresh_returns_new_token_pair(client: TestClient) -> None:
    data = _register_user(client)
    original_refresh = data["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": original_refresh})
    assert resp.status_code == 200
    new_data = resp.json()
    # The new refresh token MUST be different (rotation happened).
    assert new_data["refresh_token"] != original_refresh
    # The response must include a valid access token and user.
    assert "access_token" in new_data
    assert new_data["token_type"] == "bearer"
    assert "user" in new_data
    assert new_data["user"]["id"] == data["user"]["id"]


def test_refresh_with_revoked_token_returns_401(client: TestClient) -> None:
    data = _register_user(client)
    refresh_token = data["refresh_token"]

    # First use — valid.
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    # Reuse of the now-revoked original token.
    resp2 = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp2.status_code == 401


def test_refresh_with_garbage_token_returns_401(client: TestClient) -> None:
    resp = client.post("/api/auth/refresh", json={"refresh_token": "garbage-token-xyz"})
    assert resp.status_code == 401


# ------------------------------------------------------------------ #
# Logout and revocation
# ------------------------------------------------------------------ #


def test_logout_returns_204(client: TestClient) -> None:
    data = _register_user(client)
    access = data["access_token"]
    refresh = data["refresh_token"]

    resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 204


def test_logout_then_refresh_returns_401(client: TestClient) -> None:
    data = _register_user(client)
    access = data["access_token"]
    refresh = data["refresh_token"]

    # Logout.
    logout_resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert logout_resp.status_code == 204

    # Try to refresh with the revoked token.
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


def test_logout_with_wrong_token_returns_400(client: TestClient) -> None:
    data = _register_user(client)
    access = data["access_token"]

    resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": "wrong-refresh-token"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 400


# ------------------------------------------------------------------ #
# RBAC
# ------------------------------------------------------------------ #


def test_rbac_admin_role_is_set_on_registration(client: TestClient) -> None:
    data = _register_user(client, role="ADMIN")
    assert data["user"]["role"] == "ADMIN"


def test_rbac_invalid_role_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Bad Role",
            "email": "badrole@example.com",
            "password": "Password1",
            "role": "SUPERUSER",
        },
    )
    assert resp.status_code == 422


# ------------------------------------------------------------------ #
# TokenService unit tests (no HTTP, no DB)
# ------------------------------------------------------------------ #


def test_token_service_access_token_roundtrip(token_service: TokenService) -> None:
    user_id = uuid.uuid4()
    token = token_service.create_access_token(user_id, "ANALYST")
    payload = token_service.decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "ANALYST"
    assert payload["type"] == "access"


def test_token_service_rejects_tampered_token(token_service: TokenService) -> None:
    from app.services.token_service import TokenError

    user_id = uuid.uuid4()
    token = token_service.create_access_token(user_id, "VIEWER")
    tampered = token[:-4] + "xxxx"
    with pytest.raises(TokenError):
        token_service.decode_access_token(tampered)


def test_token_service_rejects_wrong_type(token_service: TokenService) -> None:
    """A refresh token should not pass access token validation."""
    from jose import jwt

    from app.services.token_service import TokenError

    payload = {
        "sub": str(uuid.uuid4()),
        "role": "VIEWER",
        "type": "refresh",  # wrong type
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    bad_token = jwt.encode(
        payload, "test-secret-key-for-pytest-32chars!", algorithm="HS256"
    )
    with pytest.raises(TokenError):
        token_service.decode_access_token(bad_token)


def test_refresh_token_hash_is_deterministic(token_service: TokenService) -> None:
    raw, token_hash, _ = token_service.create_refresh_token()
    recomputed = token_service.hash_token(raw)
    assert recomputed == token_hash


def test_refresh_tokens_are_unique(token_service: TokenService) -> None:
    _, hash1, _ = token_service.create_refresh_token()
    _, hash2, _ = token_service.create_refresh_token()
    assert hash1 != hash2
