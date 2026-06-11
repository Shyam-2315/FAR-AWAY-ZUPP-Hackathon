"""Authentication and authorization business logic."""

import uuid
from datetime import UTC, datetime
from typing import Any

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService

# Single passlib context for bcrypt — auto-detects and upgrades deprecated hashes.
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(Exception):
    """Domain-level authentication/authorization error."""

    def __init__(self, message: str, *, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthService:
    """Orchestrates registration, login, token refresh, and logout."""

    def __init__(
        self,
        session: AsyncSession,
        token_service: TokenService,
    ) -> None:
        self._session = session
        self._token_svc = token_service
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._audit = AuditLogRepository(session)

    # ------------------------------------------------------------------ #
    # Password utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def hash_password(plain: str) -> str:
        return str(_pwd_ctx.hash(plain))

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        result: bool = _pwd_ctx.verify(plain, hashed)
        return result

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    async def register(
        self,
        name: str,
        email: str,
        password: str,
        role: str = "VIEWER",
        *,
        ip_address: str | None = None,
    ) -> User:
        """Create a new user account.

        FIX 2 — Dev-mode role elevation:
        When ATHENA_ENV is "development" (the default for all local runs),
        every new registration is automatically elevated to ADMIN so developers
        can immediately exercise every protected endpoint without touching the
        database manually.

        To restore the normal VIEWER default for non-local environments, set
        ATHENA_ENV=staging or ATHENA_ENV=production in your .env file — the
        override only fires when the value is exactly "development".

        Raises:
            AuthError(409): if the email is already registered.
        """
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise AuthError("Email already registered", status_code=409)

        from app.core.settings import get_settings
        from app.models.enums import UserRole

        # ------------------------------------------------------------------
        # Determine the effective role for this registration.
        # In development mode we ignore whatever role the caller sent and
        # always grant ADMIN so that local developers are never blocked by
        # RBAC guardrails during testing.  In every other environment the
        # caller-supplied value is used unchanged (defaults to "VIEWER").
        # ------------------------------------------------------------------
        effective_role = role
        if get_settings().athena_env.lower() == "development":
            effective_role = "ADMIN"

        user = User(
            name=name,
            email=email.lower().strip(),
            password_hash=self.hash_password(password),
            role=UserRole(effective_role),
            is_active=True,
        )
        user = await self._users.add(user)

        await self._audit.record(
            "user_registered",
            user_id=user.id,
            ip_address=ip_address,
            # Log the role that was actually assigned, not the one requested,
            # so the audit trail is truthful about what happened.
            metadata={"email": email, "role": effective_role},
        )
        return user

    # ------------------------------------------------------------------ #
    # Login
    # ------------------------------------------------------------------ #

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """Authenticate credentials and issue token pair.

        Returns:
            (access_token, refresh_token_raw, user)

        Raises:
            AuthError(401): on bad credentials or inactive account.
        """
        user = await self._users.get_by_email(email)

        # Constant-time failure path — always verify to prevent timing attacks.
        dummy_hash = "$2b$12$000000000000000000000000000000000000000000000000000000"
        if user is None or not self.verify_password(password, user.password_hash or dummy_hash):
            await self._audit.record(
                "login_failed",
                ip_address=ip_address,
                metadata={"email": email, "reason": "invalid_credentials"},
            )
            raise AuthError("Invalid email or password")

        if not user.is_active:
            await self._audit.record(
                "login_failed",
                user_id=user.id,
                ip_address=ip_address,
                metadata={"email": email, "reason": "account_inactive"},
            )
            raise AuthError("Account is deactivated")

        access_token = self._token_svc.create_access_token(user.id, user.role.value)
        raw_refresh, token_hash, expires_at = self._token_svc.create_refresh_token()

        rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(rt)

        # Clean up old expired tokens while we're here.
        await self._refresh_tokens.prune_expired(user.id)

        await self._audit.record(
            "login_success",
            user_id=user.id,
            ip_address=ip_address,
            metadata={"email": email},
        )
        return access_token, raw_refresh, user

    # ------------------------------------------------------------------ #
    # Token refresh (rotation)
    # ------------------------------------------------------------------ #

    async def refresh(
        self,
        raw_refresh_token: str,
        *,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """Rotate a refresh token and issue a new access token.

        Implements refresh-token rotation: the old token is revoked and
        a new one is issued atomically.

        Raises:
            AuthError(401): on invalid, expired, or revoked token.
        """
        token_hash = self._token_svc.hash_token(raw_refresh_token)
        rt = await self._refresh_tokens.get_by_hash(token_hash)

        if rt is None or rt.revoked:
            # If someone tries to reuse a revoked token it may indicate theft.
            # Revoke all tokens for that user if we can identify them.
            if rt is not None:
                await self._refresh_tokens.revoke_all_for_user(rt.user_id)
                await self._audit.record(
                    "token_reuse_detected",
                    user_id=rt.user_id,
                    ip_address=ip_address,
                    metadata={"action": "all_sessions_revoked"},
                )
            raise AuthError("Refresh token is invalid or has been revoked")

        if rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            await self._audit.record(
                "token_refresh_failed",
                user_id=rt.user_id,
                ip_address=ip_address,
                metadata={"reason": "expired"},
            )
            raise AuthError("Refresh token has expired")

        user = await self._users.get_by_id(rt.user_id)
        if user is None or not user.is_active:
            raise AuthError("User not found or deactivated")

        # Issue new tokens.
        new_access = self._token_svc.create_access_token(user.id, user.role.value)
        new_raw, new_hash, new_expires = self._token_svc.create_refresh_token()

        # Revoke the old token, record successor hash for the audit chain.
        await self._refresh_tokens.revoke(rt, replaced_by=new_hash)

        new_rt = RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=new_expires,
        )
        self._session.add(new_rt)

        await self._audit.record(
            "token_refresh_success",
            user_id=user.id,
            ip_address=ip_address,
            metadata={},
        )
        return new_access, new_raw, user

    # ------------------------------------------------------------------ #
    # Logout
    # ------------------------------------------------------------------ #

    async def logout(
        self,
        raw_refresh_token: str,
        user_id: uuid.UUID,
        *,
        ip_address: str | None = None,
    ) -> None:
        """Revoke the provided refresh token (single-device logout).

        Raises:
            AuthError(400): if the token is not found or doesn't belong to the user.
        """
        token_hash = self._token_svc.hash_token(raw_refresh_token)
        rt = await self._refresh_tokens.get_by_hash(token_hash)

        if rt is None or rt.user_id != user_id:
            raise AuthError("Refresh token not found", status_code=400)

        await self._refresh_tokens.revoke(rt)
        await self._audit.record(
            "logout",
            user_id=user_id,
            ip_address=ip_address,
            metadata={},
        )

    # ------------------------------------------------------------------ #
    # Current user resolution (used by the /me endpoint)
    # ------------------------------------------------------------------ #

    async def get_current_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthError("User not found or deactivated")
        return user

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _extract_user_id(self, payload: dict[str, Any]) -> uuid.UUID:
        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise AuthError("Invalid token subject") from exc