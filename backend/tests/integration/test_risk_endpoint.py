"""Endpoint tests for GET /portfolios/{id}/risk.

Uses the conftest async_client (real Postgres via dependency override of
get_db) plus a fake in-memory Redis injected through get_redis.
"""

from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.auth.models import User
from app.deps import get_current_user, get_redis
from app.main import app
from app.portfolios.models import Portfolio


class FakeRedis:
    """Minimal stand-in exposing just the call the risk service makes."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.data.get(key, {}))


@pytest_asyncio.fixture
async def risk_client(
    async_client: AsyncClient, db_session
) -> tuple[AsyncClient, User, FakeRedis]:
    user = User(email=f"risk-{uuid.uuid4().hex[:8]}@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    fake_redis = FakeRedis()

    async def _override_user() -> User:
        return user

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_redis] = _override_redis

    yield async_client, user, fake_redis

    app.dependency_overrides.clear()


async def _make_portfolio(db_session, user: User, name: str = "Risk P") -> Portfolio:
    portfolio = Portfolio(user_id=user.id, name=name, source="demo", currency="USD")
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    return portfolio


_READY_RISK = json.dumps(
    {
        "data_status": "ready",
        "metrics": {
            "var_95": 10.0,
            "cvar_95": 15.0,
            "volatility": 0.2,
            "sharpe": 1.1,
            "max_drawdown": 0.05,
            "n_obs": 30,
        },
        "risk_contributions": [],
    }
)


@pytest.mark.asyncio
async def test_pending_when_no_state(
    risk_client: tuple[AsyncClient, User, FakeRedis], db_session
) -> None:
    client, user, _fake = risk_client
    portfolio = await _make_portfolio(db_session, user)

    resp = await client.get(f"/portfolios/{portfolio.id}/risk")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data_status"] == "pending"
    assert body["metrics"] is None


@pytest.mark.asyncio
async def test_ready_maps_metrics_and_merged_fast_path_fields(
    risk_client: tuple[AsyncClient, User, FakeRedis], db_session
) -> None:
    client, user, fake = risk_client
    portfolio = await _make_portfolio(db_session, user)
    fake.data[f"risk_state:{portfolio.id}"] = {
        "portfolio_value": "1500.00",
        "daily_pnl": "10.00",
        "risk": _READY_RISK,
    }

    resp = await client.get(f"/portfolios/{portfolio.id}/risk")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data_status"] == "ready"
    assert body["metrics"]["var_95"] == 10.0
    assert body["portfolio_value"] == "1500.00"
    assert body["daily_pnl"] == "10.00"


@pytest.mark.asyncio
async def test_cross_user_is_forbidden(
    risk_client: tuple[AsyncClient, User, FakeRedis], db_session
) -> None:
    client, _user, _fake = risk_client
    other = User(email=f"other-{uuid.uuid4().hex[:8]}@test.com", password_hash="hash")
    db_session.add(other)
    await db_session.flush()
    portfolio = await _make_portfolio(db_session, other)

    resp = await client.get(f"/portfolios/{portfolio.id}/risk")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_missing_portfolio_is_not_found(
    risk_client: tuple[AsyncClient, User, FakeRedis], _db_session
) -> None:
    client, _user, _fake = risk_client
    resp = await client.get(f"/portfolios/{uuid.uuid4()}/risk")
    assert resp.status_code == 404
