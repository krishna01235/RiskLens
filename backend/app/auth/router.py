"""auth/router.py — Register/login/refresh/logout endpoints (§7.1).

Cookie spec (refresh_token):
  HttpOnly=True, SameSite=lax, Secure determined by COOKIE_SECURE env var.
  The raw token value is only ever in the cookie; only its SHA-256 hash lives in
  the database.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.database import get_db

router = APIRouter(tags=["auth"])

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
        secure=False,  # set to True behind HTTPS in production
        max_age=_REFRESH_MAX_AGE,
        path="/auth",  # scoped to /auth so the cookie isn't sent to every route
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/auth")


# ── POST /auth/register ───────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Create a new account and return a token pair.

    Sets an httpOnly refresh cookie; returns the access token in the body.
    409 if the email is already registered.
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
async def login(
    request: Request,  # noqa: ARG001  # kept for potential future rate-limit key
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Authenticate and return a token pair.

    Sets an httpOnly refresh cookie; returns the access token in the body.
    401 on invalid credentials.

    Rate limiting (5/minute/IP) is applied via the slowapi limiter registered in
    main.py.  The ``request`` parameter is required by slowapi even if unused
    directly here.
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
async def refresh_token(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token.

    Reads the refresh cookie (httpOnly), issues a new cookie + access token.
    401 if the cookie is missing, invalid, expired, or already revoked.
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
