"""Authentication routes.

POST /api/auth/register  – create account
POST /api/auth/login     – exchange credentials for token pair
POST /api/auth/refresh   – rotate refresh token, get new access token
POST /api/auth/logout    – revoke refresh token
GET  /api/auth/me        – return authenticated user profile
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_token_service
from app.db.session import get_db_session
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import AuthError, AuthService
from app.services.token_service import TokenService

router = APIRouter(tags=["auth"])


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _build_auth_service(
    session: AsyncSession,
    token_service: TokenService,
) -> AuthService:
    return AuthService(session, token_service)


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    body: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> TokenResponse:
    svc = _build_auth_service(session, token_service)
    try:
        user = await svc.register(
            name=body.name,
            email=body.email,
            password=body.password,
            role=body.role,
            ip_address=_client_ip(request),
        )
        access_token, raw_refresh, _ = await svc.login(
            email=body.email,
            password=body.password,
            ip_address=_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT token pair",
)
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> TokenResponse:
    svc = _build_auth_service(session, token_service)
    try:
        access_token, raw_refresh, user = await svc.login(
            email=body.email,
            password=body.password,
            ip_address=_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and receive a new access token",
)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> TokenResponse:
    svc = _build_auth_service(session, token_service)
    try:
        new_access, new_refresh, user = await svc.refresh(
            raw_refresh_token=body.refresh_token,
            ip_address=_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token (single-device logout)",
)
async def logout(
    body: LogoutRequest,
    request: Request,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> None:
    svc = _build_auth_service(session, token_service)
    try:
        await svc.logout(
            raw_refresh_token=body.refresh_token,
            user_id=current_user.id,
            ip_address=_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the authenticated user's profile",
)
async def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(current_user))
