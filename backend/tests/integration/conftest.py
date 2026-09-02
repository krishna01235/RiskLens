"""tests/integration/conftest.py — Shared integration test fixtures."""

import os
import uuid
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db

import app.auth.models  # noqa: F401
import app.portfolios.models  # noqa: F401
import app.risk.models  # noqa: F401
import app.alerts.models  # noqa: F401
import app.simulations.models  # noqa: F401
import app.replays.models  # noqa: F401
import app.ai.models  # noqa: F401

from app.main import app
from app.auth.models import User


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set; skipping integration tests")
    return url


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_url: str):
    """Run Alembic migrations automatically before integration tests."""
    from alembic import command
    from alembic.config import Config
    
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture(scope="function")
async def async_engine(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean session that rolls back after each test."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def async_client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with the test DB session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com", password_hash="fakehash")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture()
async def other_test_user(db_session: AsyncSession) -> User:
    user = User(email=f"other-{uuid.uuid4().hex[:8]}@example.com", password_hash="fakehash")
    db_session.add(user)
    await db_session.flush()
    return user
