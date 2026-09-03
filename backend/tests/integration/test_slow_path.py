"""Integration tests for slow-path worker components (real Postgres, fake Redis).

Follows the repo's pattern from test_fast_path.py / test_reverse_index.py:
skipped automatically when DATABASE_URL is not set (see conftest.py).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.auth.models import User
from app.database import async_session_factory
from app.portfolios.models import Holding, Portfolio
from app.risk.models import RiskSnapshot
from quant.risk_metrics import RiskEstimate
from workers.slow_path_worker import (
    _flush_portfolio,
    persist_snapshot,
    recompute_portfolio,
)


class FakeRedis:
    """In-memory stand-in for the Redis calls the slow-path worker makes."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}
        self.published: list[tuple[str, str]] = []

    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: str | None = None,
        mapping: dict[str, str] | None = None,
    ) -> None:
        self.data.setdefault(key, {})
        if mapping:
            self.data[key].update({str(k): str(v) for k, v in mapping.items()})
        elif field is not None:
            self.data[key][field] = value

    async def hget(self, key: str, field: str) -> str | None:
        return self.data.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.data.get(key, {}))

    async def hkeys(self, key: str) -> list[str]:
        return list(self.data.get(key, {}))

    async def hdel(self, key: str, *fields: str) -> None:
        for field in fields:
            self.data.get(key, {}).pop(field, None)

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))


class _SessionFactory:
    """Minimal async-context-manager session factory wrapping a test session."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self) -> _SessionFactory:
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def make_history(
    symbols: list[str], n_days: int = 60, seed: int = 0
) -> dict[str, dict[str, str]]:
    """Synthetic noisy random-walk daily close history for *symbols*."""
    rng = np.random.default_rng(seed)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    days = [(base + timedelta(days=i)).date().isoformat() for i in range(n_days)]
    history: dict[str, dict[str, str]] = {}
    for sym in symbols:
        price = 100.0
        history[sym] = {}
        for day in days:
            price *= 1.0 + rng.normal(0.0005, 0.02)
            history[sym][day] = str(price)
    return history


@pytest_asyncio.fixture
async def slow_path_user(db_session) -> User:
    user = User(email=f"slowpath-{uuid.uuid4().hex[:8]}@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def portfolio_with_holding(db_session, slow_path_user: User) -> Portfolio:
    portfolio = Portfolio(
        user_id=slow_path_user.id,
        name="Slow Path",
        source="demo",
        currency="USD",
    )
    db_session.add(portfolio)
    await db_session.flush()
    db_session.add(
        Holding(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            quantity=Decimal("10"),
            average_price=Decimal("150"),
        )
    )
    await db_session.commit()
    await db_session.refresh(portfolio)
    return portfolio


@pytest.mark.asyncio
async def test_recompute_ready_writes_state_and_publishes(
    db_session, portfolio_with_holding: Portfolio
) -> None:
    redis = FakeRedis()
    pid = str(portfolio_with_holding.id)
    await redis.hset("price_history:AAPL", mapping=make_history(["AAPL"]))
    await redis.hset(f"risk_state:{pid}", "portfolio_value", "1500.00")

    await recompute_portfolio(db_session, redis, pid, "", set())

    risk_data = json.loads(redis.data[f"risk_state:{pid}"]["risk"])
    assert risk_data["data_status"] == "ready"
    assert risk_data["metrics"]["var_95"] > 0

    assert len(redis.published) == 1
    channel, payload = redis.published[0]
    assert channel == f"risk_updates:{pid}"
    body = json.loads(payload)
    assert body["portfolio_id"] == pid
    assert body["portfolio_value"] == "1500.00"


@pytest.mark.asyncio
async def test_recompute_insufficient_without_history_is_explicit(
    db_session, portfolio_with_holding: Portfolio
) -> None:
    redis = FakeRedis()
    pid = str(portfolio_with_holding.id)

    await recompute_portfolio(db_session, redis, pid, "", set())

    state_json = await redis.hget(f"risk_state:{pid}", "risk")
    state = json.loads(state_json)
    assert state["data_status"] == "insufficient_data"
    assert state["metrics"] is None


@pytest.mark.asyncio
async def test_recompute_demo_portfolio_generates_correlation_flags(
    db_session, slow_path_user: User
) -> None:
    """Test that a portfolio with highly correlated assets gets flagged."""
    from app.portfolios.service import create_demo_portfolio
    
    redis = FakeRedis()
    
    # Create the demo portfolio (which contains AMD, NVDA, INTC)
    portfolio = await create_demo_portfolio(db_session, slow_path_user.id)
    pid = str(portfolio.id)
    
    # Generate synthetic price history with high correlation for semis
    # and low correlation for the others (JNJ)
    base_trend = np.linspace(100, 150, 50)
    # Semiconductors move together strongly
    nvda_prices = base_trend + np.random.normal(0, 2, 50)
    amd_prices = base_trend + np.random.normal(0, 2, 50)
    intc_prices = base_trend + np.random.normal(0, 2, 50)
    # JNJ is uncorrelated
    jnj_prices = np.linspace(50, 55, 50) + np.random.normal(0, 1, 50)
    
    history_dict = {
        "NVDA": nvda_prices,
        "AMD": amd_prices,
        "INTC": intc_prices,
        "JNJ": jnj_prices,
    }
    
    # Write to fake redis
    for symbol, prices in history_dict.items():
        mapping = {}
        for i, price in enumerate(prices):
            # mock dates
            day = (datetime(2023, 1, 1) + timedelta(days=i)).date().isoformat()
            mapping[day] = str(price)
        await redis.hset(f"price_history:{symbol}", mapping=mapping)
        
    await recompute_portfolio(db_session, redis, pid, "fake_key", set())
    
    # Verify the state in Redis
    state_json = await redis.hget(f"risk_state:{pid}", "risk")
    assert state_json is not None
    
    state = json.loads(state_json)
    assert state["data_status"] == "ready"
    assert state["metrics"] is not None
    
    # Verify risk contributions are populated
    rcs = state["risk_contributions"]
    assert len(rcs) == 4
    for rc in rcs:
        assert "symbol" in rc
        assert "rc_pct" in rc
        
    # Verify correlation flags caught the semiconductor cluster
    flags = state["correlation_flags"]
    assert len(flags) > 0
    # There should be at least one cluster containing NVDA, AMD, INTC
    semi_cluster = next((c for c in flags if "NVDA" in c and "AMD" in c), None)
    assert semi_cluster is not None, f"Flags were: {flags}"


@pytest.mark.asyncio
async def test_persist_snapshot_writes_row(
    db_session, portfolio_with_holding: Portfolio
) -> None:
    estimate = RiskEstimate(
        volatility=0.25,
        var_95=Decimal("100.00"),
        cvar_95=Decimal("150.00"),
        sharpe=1.5,
        max_drawdown=0.2,
    )
    await persist_snapshot(
        db_session, str(portfolio_with_holding.id), estimate, datetime.now(UTC)
    )

    result = await db_session.execute(
        select(RiskSnapshot).where(
            RiskSnapshot.portfolio_id == portfolio_with_holding.id
        )
    )
    row = result.scalar_one()
    assert float(row.var_95) == 100.00
    assert float(row.volatility) == 0.25
    assert row.risk_state == "SAFE"


@pytest.mark.asyncio
async def test_flush_portfolio_isolation_does_not_stop_others(
    db_session,
) -> None:
    """F5 Errors rule: one failing portfolio must not stop the rest."""
    async with async_session_factory() as db:
        user = User(
            email=f"isolate-{uuid.uuid4().hex[:8]}@test.com", password_hash="hash"
        )
        db.add(user)
        await db.flush()
        p1 = Portfolio(user_id=user.id, name="P1", source="demo")
        p2 = Portfolio(user_id=user.id, name="P2", source="demo")
        db.add(p1)
        await db.flush()
        db.add(p2)
        await db.commit()
        p1_id, p2_id = str(p1.id), str(p2.id)
        user_id = user.id

    redis = FakeRedis()
    calls: list[str] = []

    async def boom(db, redis_client, pid: str, key: str, seeded: set[str]) -> None:
        calls.append(pid)
        if pid == p1_id:
            raise RuntimeError("boom")

    factory = _SessionFactory(db_session)
    with patch("workers.slow_path_worker.recompute_portfolio", side_effect=boom):
        await _flush_portfolio(factory, redis, p1_id, "", set(), {}, 0.0)
        await _flush_portfolio(factory, redis, p2_id, "", set(), {}, 0.0)

    assert calls == [p1_id, p2_id], "both portfolios processed despite p1 failing"

    # Cleanup the portfolios created through the real session factory.
    async with async_session_factory() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
