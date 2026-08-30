"""tests/unit/test_auth_service.py — Unit tests for password hashing and JWT.

These tests are purely in-process; no database or network required.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from jose import JWTError

from app.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


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
