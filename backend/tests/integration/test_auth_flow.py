"""tests/integration/test_auth_flow.py — Full auth cycle integration tests.

Requires a live Postgres instance (DATABASE_URL env var).
Run with:
    DATABASE_URL=postgresql+asyncpg://... pytest tests/integration/test_auth_flow.py -v

The test suite uses httpx.AsyncClient against the real FastAPI app with a real
(test-isolated) database session so we exercise the full stack — middleware,
router, service, and DB — in one go.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set; skipping integration tests")
    return url


@pytest_asyncio.fixture(scope="module")
async def async_engine(db_url: str):  # type: ignore[no-untyped-def]
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(async_engine):  # type: ignore[no-untyped-def]
    """Provide a clean session that rolls back after each test."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """AsyncClient wired to the FastAPI app with the test DB session."""

    async def override_get_db():  # type: ignore[no-untyped-def]
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Helper ────────────────────────────────────────────────────────────────────


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(client: httpx.AsyncClient) -> None:
    """201 + access_token in body + httpOnly refresh cookie set."""
    resp = await client.post(
        "/auth/register", json={"email": _unique_email(), "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client: httpx.AsyncClient) -> None:
    """409 when the same email is registered twice."""
    email = _unique_email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient) -> None:
    """200 + access_token after valid login."""
    email = _unique_email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: httpx.AsyncClient) -> None:
    """401 on incorrect password."""
    email = _unique_email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: httpx.AsyncClient) -> None:
    """401 when the email does not exist (must not reveal whether user exists)."""
    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(client: httpx.AsyncClient) -> None:
    """Refresh issues a new access_token and rotates the cookie."""
    email = _unique_email()
    reg = await client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    original_token = reg.json()["access_token"]
    original_cookie = reg.cookies["refresh_token"]

    resp = await client.post("/auth/refresh")
    assert resp.status_code == 200
    new_body = resp.json()
    assert "access_token" in new_body
    # New access token must differ from the original
    assert new_body["access_token"] != original_token
    # Cookie must have been rotated (new value)
    assert resp.cookies.get("refresh_token", original_cookie) != original_cookie


@pytest.mark.asyncio
async def test_refresh_after_logout(client: httpx.AsyncClient) -> None:
    """After logout, the old refresh token must be rejected (401)."""
    email = _unique_email()
    await client.post("/auth/register", json={"email": email, "password": "password123"})

    logout_resp = await client.post("/auth/logout")
    assert logout_resp.status_code == 204

    # Cookie should be cleared by logout; attempt refresh anyway
    refresh_resp = await client.post("/auth/refresh")
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: httpx.AsyncClient) -> None:
    """Calling get_current_user with no Bearer header must return 401."""
    # We use /auth/logout (which requires a refresh cookie, not Bearer) as a proxy
    # test for the dependency by directly testing the oauth2 scheme behaviour.
    # A simpler direct test: hit a route that uses get_current_user with no header.
    # Since no protected domain routes exist yet (Phase 5+), we validate the
    # dependency by confirming the oauth2 scheme raises 401 with no token.
    from app.deps import get_current_user
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=None, db=client)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 401
