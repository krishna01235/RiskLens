"""tests/unit/test_auth_service.py — Unit tests for password hashing and JWT.

These tests are purely in-process; no database or network required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from jose import JWTError
from sqlalchemy.engine import Result

from app.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    register,
    login,
    refresh,
    logout,
    AuthError,
    create_api_token,
    _hash_token
)
from app.auth.models import User, RefreshToken, ApiToken


# ── Password hashing ──────────────────────────────────────────────────────────


def test_hash_and_verify_password() -> None:
    """A hashed password must verify against the original plain text."""
    plain = "supersecret123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_verify_wrong_password() -> None:
    """Verification must fail when the wrong password is supplied."""
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_two_hashes_of_same_password_differ() -> None:
    """bcrypt generates a new salt each time — hashes must not be identical."""
    plain = "same-password"
    assert hash_password(plain) != hash_password(plain)


# ── JWT ───────────────────────────────────────────────────────────────────────


def test_create_access_token_decodes_correctly() -> None:
    """The decoded token must contain the correct user UUID in the `sub` claim."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    decoded_id = decode_access_token(token)
    assert decoded_id == user_id


def test_access_token_expired() -> None:
    """An access token with a past expiry must raise JWTError on decode."""
    user_id = uuid.uuid4()

    # Patch expire minutes to -1 so exp is already in the past
    with patch("app.auth.service.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.access_token_expire_minutes = -1
        settings.secret_key = "test-secret-key"
        token = create_access_token(user_id)

    with patch("app.auth.service.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.secret_key = "test-secret-key"
        with pytest.raises(JWTError):
            decode_access_token(token)


def test_token_with_wrong_secret_raises() -> None:
    """A token signed with key A must not decode successfully with key B."""
    user_id = uuid.uuid4()

    with patch("app.auth.service.get_settings") as mock:
        mock.return_value.secret_key = "secret-A"
        mock.return_value.access_token_expire_minutes = 15
        token = create_access_token(user_id)

    with patch("app.auth.service.get_settings") as mock:
        mock.return_value.secret_key = "secret-B"
        with pytest.raises(JWTError):
            decode_access_token(token)


# ── Service Functions (Mocked DB) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_new_user() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    user, access, refresh_token = await register(db, "test@example.com", "pass")
    assert user.email == "test@example.com"
    assert access
    assert refresh_token
    assert db.add.called
    assert db.commit.called


@pytest.mark.asyncio
async def test_register_existing_user() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = User(email="test@example.com")
    db.execute.return_value = mock_result
    
    with pytest.raises(AuthError) as exc:
        await register(db, "test@example.com", "pass")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_success() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash=hash_password("pass"))
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = user
    db.execute.return_value = mock_result
    
    user_ret, access, refresh_token = await login(db, "test@example.com", "pass")
    assert user_ret == user
    assert access
    assert refresh_token


@pytest.mark.asyncio
async def test_login_bad_credentials() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    with pytest.raises(AuthError) as exc:
        await login(db, "test@example.com", "wrong")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    user = User(id=uuid.uuid4(), email="test@example.com")
    rt = RefreshToken(user_id=user.id, token_hash=_hash_token("raw_token"), user=user)
    
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = rt
    db.execute.return_value = mock_result
    
    new_access, new_refresh = await refresh(db, "raw_token")
    assert new_access
    assert new_refresh
    assert rt.revoked_at is not None
    assert db.add.called


@pytest.mark.asyncio
async def test_refresh_invalid() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    with pytest.raises(AuthError) as exc:
        await refresh(db, "bad_token")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_revoked() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    user = User(id=uuid.uuid4(), email="test@example.com")
    rt = RefreshToken(user_id=user.id, token_hash=_hash_token("raw_token"), user=user, revoked_at=datetime.now(UTC))
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = rt
    db.execute.return_value = mock_result
    
    with pytest.raises(AuthError) as exc:
        await refresh(db, "raw_token")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_logout() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    rt = RefreshToken(token_hash=_hash_token("raw_token"))
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = rt
    db.execute.return_value = mock_result
    
    await logout(db, "raw_token")
    assert rt.revoked_at is not None
    assert db.commit.called


@pytest.mark.asyncio
async def test_create_api_token() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    user = User(id=uuid.uuid4(), email="test@example.com")
    
    token = await create_api_token(db, user.id, "Slack", ["read", "whatif"])
    assert token.startswith("rl_")
    assert db.add.called
    assert db.commit.called
