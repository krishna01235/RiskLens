"""tests/test_fast_path.py — Integration tests for fast_path_worker."""

import asyncio
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.auth.models import User
from app.portfolios.models import Portfolio, Holding
from workers.fast_path_worker import HOLDINGS_CACHE, LATEST_PRICES, load_holdings

@pytest_asyncio.fixture
async def sample_user(db: AsyncSession) -> User:
    user = User(email="fastpath@test.com", password_hash="hash")
    db.add(user)
    await db.commit()
    return user

@pytest_asyncio.fixture
async def sample_portfolio(db: AsyncSession, sample_user: User) -> Portfolio:
    portfolio = Portfolio(
        user_id=sample_user.id,
        name="Test Fast Path",
        source="demo",
        currency="USD"
    )
    db.add(portfolio)
    await db.flush()

    holding1 = Holding(
        portfolio_id=portfolio.id,
        symbol="AAPL",
        quantity=Decimal("10"),
        average_price=Decimal("150.0")
    )
    db.add(holding1)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio

@pytest.mark.asyncio
async def test_load_holdings_cache(db: AsyncSession, sample_portfolio: Portfolio):
    pid_str = str(sample_portfolio.id)
    
    # Clear cache
    HOLDINGS_CACHE.clear()
    
    # Load holdings
    holdings = await load_holdings(db, pid_str)
    
    assert holdings is not None
    assert "AAPL" in holdings
    assert holdings["AAPL"]["quantity"] == Decimal("10")
    assert holdings["AAPL"]["average_price"] == Decimal("150.0")
    
    assert pid_str in HOLDINGS_CACHE

