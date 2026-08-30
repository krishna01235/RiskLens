"""auth/service.py — Password hashing, JWT encode/decode, register/login/refresh/logout.

This module is intentionally free of FastAPI imports so every function can be
unit-tested without spinning up an ASGI app.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.config import get_settings

# ── Password hashing ──────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID) -> str:
    """Issue a short-lived HS256 JWT.

    Payload: ``{sub: str(user_id), exp: <utcnow + access_token_expire_minutes>}``.
    No sensitive data is included because the JWT body is only base64-encoded,
    not encrypted.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Decode and validate *token*; return the user UUID from ``sub``.

    Raises :class:`jose.JWTError` on any failure (expired, malformed, bad sig).
    """
    settings = get_settings()
    data = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    sub: str | None = data.get("sub")
    if sub is None:
        raise JWTError("Missing 'sub' claim")
    return uuid.UUID(sub)


# ── Refresh token helpers ─────────────────────────────────────────────────────


def _hash_token(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*.

    Only the hash is persisted; the raw value travels in the httpOnly cookie.
    """
    return hashlib.sha256(raw.encode()).hexdigest()


async def _create_refresh_token_record(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[str, RefreshToken]:
    """Generate a new refresh token, persist its hash, return (raw, record)."""
    settings = get_settings()
    raw = secrets.token_hex(32)
    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(record)
    await db.flush()  # get the id without committing the outer transaction
    return raw, record


async def _revoke_token_by_hash(db: AsyncSession, token_hash: str) -> None:
    """Mark the refresh token row with *token_hash* as revoked (best-effort)."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)


# ── Public service functions ───────────────────────────────────────────────────


class AuthError(Exception):
    """Raised when an auth operation fails; callers map to HTTP status codes."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


async def register(
    db: AsyncSession, email: str, password: str
) -> tuple[User, str, str]:
    """Create a new user account.

    Returns ``(user, access_token, raw_refresh_token)``.
    Raises :class:`AuthError` (409) if the email is already registered.
    """
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise AuthError("Email already registered.", status_code=409)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()  # populate user.id

    access_token = create_access_token(user.id)
    raw_refresh, _ = await _create_refresh_token_record(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user, access_token, raw_refresh


async def login(
    db: AsyncSession, email: str, password: str
) -> tuple[User, str, str]:
    """Authenticate a user and issue a new token pair.

    Returns ``(user, access_token, raw_refresh_token)``.
    Raises :class:`AuthError` (401) on bad credentials.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.", status_code=401)

    access_token = create_access_token(user.id)
    raw_refresh, _ = await _create_refresh_token_record(db, user.id)
    await db.commit()
    return user, access_token, raw_refresh


async def refresh(
    db: AsyncSession, raw_refresh_token: str
) -> tuple[str, str]:
    """Rotate a refresh token and issue a new access token.

    Returns ``(new_access_token, new_raw_refresh_token)``.
    Raises :class:`AuthError` (401) if the token is invalid, expired, or revoked.

    Known MVP simplification: no grace-window for concurrent-tab race.
    In production, consider accepting the immediately-prior token hash for a
    short window (e.g., 5 s) to handle two-tab simultaneous refreshes.
    """
    token_hash = _hash_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if record is None:
        raise AuthError("Refresh token not found.", status_code=401)
    if record.revoked_at is not None:
        raise AuthError("Refresh token has been revoked.", status_code=401)
    # expires_at may be timezone-naive (DB stores UTC without tz info)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise AuthError("Refresh token has expired.", status_code=401)

    # Rotate: revoke old, issue new
    record.revoked_at = now
    new_access = create_access_token(record.user_id)
    new_raw, _ = await _create_refresh_token_record(db, record.user_id)
    await db.commit()
    return new_access, new_raw


async def logout(db: AsyncSession, raw_refresh_token: str) -> None:
    """Revoke the current refresh token.

    Silently succeeds if the token is already revoked or not found
    (idempotent — a double-logout should not error).
    """
    token_hash = _hash_token(raw_refresh_token)
    await _revoke_token_by_hash(db, token_hash)
    await db.commit()
