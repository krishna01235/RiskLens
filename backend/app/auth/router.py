"""auth/router.py — Register/login/refresh/logout endpoints (§7.1).

Cookie spec (refresh_token):
  HttpOnly=True, SameSite=lax, Secure determined by COOKIE_SECURE env var.
  The raw token value is only ever in the cookie; only its SHA-256 hash lives in
  the database.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.constants import ALLOWED_SCOPES, ONE_TIME_CODE_TTL_SECONDS
from app.auth.models import User
from app.auth.schemas import (
    ApiTokenCreateRequest,
    ApiTokenResponse,
    LoginRequest,
    OneTimeCodeResponse,
    RegisterRequest,
    TokenResponse,
)
from app.database import get_db
from app.deps import get_current_user, get_redis, limiter
from app.config import get_settings

router = APIRouter(tags=["auth"])
_settings = get_settings()

# Cookie name used for the refresh token
_REFRESH_COOKIE = "refresh_token"
# 7 days in seconds (must stay in sync with settings.refresh_token_expire_days)
_REFRESH_MAX_AGE = 7 * 24 * 60 * 60


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=_settings.cookie_secure,  # True in production (HTTPS); set via COOKIE_SECURE env var
        max_age=_REFRESH_MAX_AGE,
        path="/auth",  # scoped to /auth so the cookie isn't sent to every route
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/auth")


# ── POST /auth/register ───────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("10/minute")
async def register(
    body: RegisterRequest,
    request: Request,  # noqa: ARG001  # required by slowapi
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Create a new account and return a token pair.

    Sets an httpOnly refresh cookie; returns the access token in the body.
    409 if the email is already registered.
    Rate limited to 10 requests per minute per IP.
    """
    try:
        _user, access_token, raw_refresh = await service.register(
            db, body.email, body.password
        )
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access_token)


# ── POST /auth/login ──────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,  # required by slowapi
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Authenticate and return a token pair.

    Sets an httpOnly refresh cookie; returns the access token in the body.
    401 on invalid credentials.
    Rate limited to 5 requests per minute per IP.
    """
    try:
        _user, access_token, raw_refresh = await service.login(
            db, body.email, body.password
        )
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access_token)


# ── POST /auth/refresh ────────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,  # noqa: ARG001  # required by slowapi
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token.

    Reads the refresh cookie (httpOnly), issues a new cookie + access token.
    401 if the cookie is missing, invalid, expired, or already revoked.
    Rate limited to 10 requests per minute per IP.
    """
    if refresh_token_cookie is None:
        raise HTTPException(status_code=401, detail="Refresh token cookie missing.")

    try:
        new_access, new_raw = await service.refresh(db, refresh_token_cookie)
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=new_access)


# ── POST /auth/logout ─────────────────────────────────────────────────────────


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Revoke the current refresh token and clear the cookie.

    Idempotent — calling logout twice is safe.
    """
    if refresh_token_cookie is not None:
        await service.logout(db, refresh_token_cookie)
    _clear_refresh_cookie(response)


# ── POST /auth/api-tokens ──────────────────────────────────────────────────────


@router.post("/api-tokens", response_model=ApiTokenResponse, status_code=201)
@limiter.limit("5/minute")
async def create_api_token(
    body: ApiTokenCreateRequest,
    request: Request,  # noqa: ARG001  # required by slowapi
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ApiTokenResponse:
    """Issue a new scoped API token for the authenticated user.

    The ``raw_token`` field is returned **once only** — it cannot be retrieved
    again after this response.  Store it securely immediately.

    Allowed scopes: ``read``, ``whatif``.
    Rate limited to 5 requests per minute.
    """
    try:
        raw_token, record = await service.create_api_token(
            db, current_user.id, body.scopes
        )
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return ApiTokenResponse(
        id=record.id,
        raw_token=raw_token,
        scopes=record.scopes,
        created_at=record.created_at,
    )


# ── DELETE /auth/api-tokens/{token_id} ────────────────────────────────────────


@router.delete("/api-tokens/{token_id}", status_code=204)
@limiter.limit("10/minute")
async def revoke_api_token(
    token_id: uuid.UUID,
    request: Request,  # noqa: ARG001  # required by slowapi
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    """Revoke a previously issued API token.

    403 if the token belongs to another user; 404 if not found.
    Rate limited to 10 requests per minute per IP.
    """
    try:
        await service.revoke_api_token(db, token_id, current_user.id)
    except service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


# ── POST /auth/api-tokens/one-time-code ───────────────────────────────────────


@router.post(
    "/api-tokens/one-time-code",
    response_model=OneTimeCodeResponse,
    status_code=201,
)
@limiter.limit("10/minute")
async def create_one_time_code(
    request: Request,  # noqa: ARG001  # required by slowapi
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis=Depends(get_redis),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> OneTimeCodeResponse:
    """Generate a short-lived one-time code for the Slack bot login flow.

    The user pastes this code into Slack via ``/risklens login <code>``.
    The code expires after {ttl}s and is single-use.

    Rate limited to 10 requests per minute.
    """.format(ttl=ONE_TIME_CODE_TTL_SECONDS)
    # Issue token with both scopes so the Slack bot can call all its endpoints.
    scopes = sorted(ALLOWED_SCOPES)
    code = await service.create_one_time_code(redis, current_user.id, scopes)
    return OneTimeCodeResponse(
        code=code,
        expires_in_seconds=ONE_TIME_CODE_TTL_SECONDS,
    )
