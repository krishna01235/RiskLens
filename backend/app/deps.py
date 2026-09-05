"""deps.py — Shared FastAPI dependencies.

Every protected endpoint imports ``get_current_user`` from this module.
Row-level ownership enforcement is done at the *service layer* of each domain
module (not just here), as required by the ownership-and-security-review skill.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import decode_access_token
from app.database import get_db
from app.config import get_settings
import redis.asyncio as redis
from collections.abc import AsyncGenerator

settings = get_settings()

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.Redis.from_pool(redis_pool)
    try:
        yield client
    finally:
        await client.aclose()

# The token URL is used only to populate the Swagger UI "Authorize" dialog.
# Actual token issuance happens in /auth/login.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """Decode the Bearer access token and return the authenticated User.

    Raises HTTP 401 if:
    - No Authorization header is present
    - The token is expired, malformed, or has an invalid signature
    - The user UUID in the token no longer exists in the database

    Usage::

        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        user_id: uuid.UUID = decode_access_token(token)
    except (JWTError, ValueError):
        raise credentials_exception from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


def get_current_user_any(required_scope: str):
    """Return a FastAPI dependency that accepts *either* a JWT bearer token
    or a scoped API token carrying ``required_scope``.

    Strategy (tried in order):
    1. Try to decode the bearer value as a JWT access token.
       If that succeeds the caller is an authenticated web-dashboard user —
       no scope restriction applies (matches existing ``get_current_user``
       behaviour exactly).
    2. If JWT decoding fails, try the same bearer value as a raw API token
       and validate that it carries ``required_scope``.
       - Valid token, wrong scope  → HTTP 403
       - Missing / revoked token   → HTTP 401

    Only the four Slack-bot-facing routes use this dependency.
    Every other endpoint keeps ``get_current_user`` unchanged.

    Usage::

        @router.get("/portfolios")
        async def list_portfolios(
            current_user: User = Depends(get_current_user_any("read")),
        ): ...
    """
    from app.auth import service as auth_service  # avoid circular at module level

    async def _dependency(
        token: str | None = Depends(_oauth2_scheme),  # noqa: B008
        db: AsyncSession = Depends(get_db),  # noqa: B008
    ) -> User:
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ── Path 1: JWT ────────────────────────────────────────────────────────
        try:
            user_id = decode_access_token(token)
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is not None:
                return user  # JWT path — no scope check needed
        except (JWTError, ValueError):
            pass  # fall through to API token path

        # ── Path 2: API token ──────────────────────────────────────────────────
        try:
            return await auth_service.validate_api_token(db, token, required_scope)
        except auth_service.AuthError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    return _dependency
