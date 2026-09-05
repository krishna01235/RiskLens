"""auth/service.py — Password hashing, JWT encode/decode, register/login/refresh/logout.

This module is intentionally free of FastAPI imports so every function can be
unit-tested without spinning up an ASGI app.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

# pyright: ignore [reportMissingImports, reportMissingModuleSource]
# pyrefly: ignore [missing-import]
import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import ALLOWED_SCOPES, API_TOKEN_BYTE_LENGTH, ONE_TIME_CODE_TTL_SECONDS
from app.auth.models import ApiToken, RefreshToken, User
from app.config import get_settings

# ── Password hashing ──────────────────────────────────────────────────────────
# Uses the `bcrypt` package directly (passlib compat issues with bcrypt>=4).


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID) -> str:
    """Issue a short-lived HS256 JWT.

    Payload: ``{sub: str(user_id), exp: <utcnow + access_token_expire_minutes>}``.
    No sensitive data is included because the JWT body is only base64-encoded,
    not encrypted.
    """
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
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
        expires_at=datetime.now(UTC)
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
        record.revoked_at = datetime.now(UTC)


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


async def login(db: AsyncSession, email: str, password: str) -> tuple[User, str, str]:
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


async def refresh(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
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

    now = datetime.now(UTC)
    if record is None:
        raise AuthError("Refresh token not found.", status_code=401)
    if record.revoked_at is not None:
        raise AuthError("Refresh token has been revoked.", status_code=401)
    # expires_at is returned as an aware datetime by asyncpg from the TIMESTAMPTZ column
    expires_at = record.expires_at
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


# ── API token helpers ──────────────────────────────────────────────────────────


async def create_api_token(
    db: AsyncSession, user_id: uuid.UUID, scopes: list[str]
) -> tuple[str, ApiToken]:
    """Issue a new scoped API token for *user_id*.

    Returns ``(raw_token, record)``.  Only *raw_token* leaves the system;
    its SHA-256 hash is what is persisted.

    Raises :class:`AuthError` (422) if any scope is not in ALLOWED_SCOPES.
    """
    invalid = set(scopes) - ALLOWED_SCOPES
    if invalid:
        raise AuthError(
            f"Invalid scope(s): {sorted(invalid)}. Allowed: {sorted(ALLOWED_SCOPES)}",
            status_code=422,
        )
    raw = secrets.token_bytes(API_TOKEN_BYTE_LENGTH).hex()
    record = ApiToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        scopes=scopes,
    )
    db.add(record)
    await db.flush()
    await db.commit()
    await db.refresh(record)
    return raw, record


async def validate_api_token(
    db: AsyncSession, raw_token: str, required_scope: str
) -> User:
    """Validate *raw_token* and confirm it carries *required_scope*.

    Returns the linked :class:`User`.

    Raises :class:`AuthError`:
    - 401 if the token is not found or has been revoked.
    - 403 if the token is valid but does not carry *required_scope*.
    """
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(ApiToken).where(ApiToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if record is None or record.revoked_at is not None:
        raise AuthError("API token not found or revoked.", status_code=401)

    if required_scope not in record.scopes:
        raise AuthError(
            f"API token lacks required scope '{required_scope}'.", status_code=403
        )

    user_result = await db.execute(select(User).where(User.id == record.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise AuthError("Token owner not found.", status_code=401)

    return user


async def revoke_api_token(
    db: AsyncSession, token_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Revoke an API token.

    Raises :class:`AuthError` (404) if not found; (403) if owned by another user.
    """
    result = await db.execute(select(ApiToken).where(ApiToken.id == token_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise AuthError("API token not found.", status_code=404)
    if record.user_id != user_id:
        raise AuthError("Cannot revoke another user's token.", status_code=403)
    if record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
    await db.commit()


# ── One-time login code helpers ────────────────────────────────────────────────


_OTC_PREFIX = "rl:otc:"


async def create_one_time_code(
    redis: object,
    user_id: uuid.UUID,
    scopes: list[str],
) -> str:
    """Store a short-lived one-time code in Redis for the Slack login flow.

    The user copies this code and pastes it into Slack via
    ``/risklens login <code>``.

    Returns the raw code string.
    """
    code = secrets.token_hex(16)  # 32-char hex string
    payload = json.dumps({"user_id": str(user_id), "scopes": scopes})
    await redis.set(f"{_OTC_PREFIX}{code}", payload, ex=ONE_TIME_CODE_TTL_SECONDS)  # type: ignore[attr-defined]
    return code


async def exchange_one_time_code(
    db: AsyncSession,
    redis: object,
    code: str,
    slack_user_id: str,
) -> tuple[str, ApiToken]:
    """Exchange a one-time code for a linked API token.

    Atomically consumes the Redis key (single-use).  Creates an ApiToken and
    a SlackLink row in one DB transaction.

    Raises :class:`AuthError` (404) if the code is missing or already consumed.
    """
    from app.auth.models import SlackLink  # local import to avoid circular

    key = f"{_OTC_PREFIX}{code}"
    # Pipeline: GET then DELETE atomically so concurrent calls can't both succeed
    pipe = redis.pipeline()  # type: ignore[attr-defined]
    pipe.get(key)
    pipe.delete(key)
    raw_payload, _ = await pipe.execute()

    if raw_payload is None:
        raise AuthError(
            "One-time code not found, already used, or expired.", status_code=404
        )

    data = json.loads(raw_payload)
    user_id = uuid.UUID(data["user_id"])
    scopes: list[str] = data["scopes"]

    # Create API token
    raw_token, api_token = await _create_api_token_no_commit(db, user_id, scopes)

    # Upsert SlackLink (replace if the user re-links)
    existing = await db.execute(
        select(SlackLink).where(SlackLink.slack_user_id == slack_user_id)
    )
    link = existing.scalar_one_or_none()
    if link is not None:
        # Revoke the old token before overwriting
        old_token_result = await db.execute(
            select(ApiToken).where(ApiToken.id == link.api_token_id)
        )
        old_token = old_token_result.scalar_one_or_none()
        if old_token is not None and old_token.revoked_at is None:
            old_token.revoked_at = datetime.now(UTC)
        link.api_token_id = api_token.id
    else:
        db.add(SlackLink(slack_user_id=slack_user_id, api_token_id=api_token.id))

    await db.commit()
    await db.refresh(api_token)
    return raw_token, api_token


async def _create_api_token_no_commit(
    db: AsyncSession, user_id: uuid.UUID, scopes: list[str]
) -> tuple[str, ApiToken]:
    """Internal helper: create ApiToken row without committing."""
    raw = secrets.token_bytes(API_TOKEN_BYTE_LENGTH).hex()
    record = ApiToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        scopes=scopes,
    )
    db.add(record)
    await db.flush()
    return raw, record


async def get_linked_api_token_raw(
    db: AsyncSession, redis: object, slack_user_id: str
) -> str | None:
    """Return the raw API token for a linked Slack user, or None if not linked.

    Note: the raw token is NOT stored in the DB — only its hash is. This
    helper reads the raw token from a short-lived Redis cache set at link time.
    The Slack bot stores the raw token in memory/session after linking.
    """
    from app.auth.models import SlackLink  # local import

    result = await db.execute(
        select(SlackLink).where(SlackLink.slack_user_id == slack_user_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        return None
    # The raw token is cached in Redis at link time under rl:rawtoken:<token_id>
    cached = await redis.get(f"rl:rawtoken:{link.api_token_id}")  # type: ignore[attr-defined]
    return cached  # type: ignore[return-value]


async def unlink_slack_user(
    db: AsyncSession, redis: object, user_id: uuid.UUID, slack_user_id: str
) -> None:
    """Revoke the linked API token and remove the SlackLink row.

    Ownership check: the SlackLink's ApiToken must belong to *user_id*.
    Raises :class:`AuthError` (404) if the user isn't linked.
    Raises :class:`AuthError` (403) if owned by another user.
    """
    from app.auth.models import SlackLink  # local import

    result = await db.execute(
        select(SlackLink).where(SlackLink.slack_user_id == slack_user_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise AuthError("No Slack link found.", status_code=404)

    token_result = await db.execute(
        select(ApiToken).where(ApiToken.id == link.api_token_id)
    )
    token = token_result.scalar_one_or_none()
    if token is not None:
        if token.user_id != user_id:
            raise AuthError("Not your Slack link.", status_code=403)
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)

    await db.delete(link)
    # Clean up cached raw token
    await redis.delete(f"rl:rawtoken:{link.api_token_id}")  # type: ignore[attr-defined]
    await db.commit()
