import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from datetime import date
import uuid

from app.portfolios.models import Portfolio, Holding, RiskBudget
from app.market.models import HistoricalPrice
from app.replays.models import Replay, ReplayDailyState, BacktestResult
from app.auth.service import create_access_token
from app.auth.models import User

@pytest.mark.asyncio
async def test_replay_lifecycle(async_client: AsyncClient, db_session: AsyncSession, test_user: User):
    auth_headers = {"Authorization": f"Bearer {create_access_token(test_user.id)}"}
    # 1. Setup Portfolio & Data
    db = db_session
    portfolio = Portfolio(id=uuid.uuid4(), user_id=test_user.id, name="Replay Test", source="manual", currency="USD")
    db.add(portfolio)
    test_symbol = f"TEST_{uuid.uuid4().hex[:6]}"
    db.add(Holding(portfolio_id=portfolio.id, symbol=test_symbol, quantity=Decimal("10.0"), average_price=Decimal("150.0")))
    db.add(RiskBudget(portfolio_id=portfolio.id, max_cvar=Decimal("1000.0")))
    
    # Add fake historical data
    for i in range(25):
        price = Decimal(str(150.0 + i))
        db.add(HistoricalPrice(symbol=test_symbol, trading_date=date(2022, 1, 1+i), open=price, high=price, low=price, close=price, volume=100))
    await db.commit()

    # 2. Trigger Replay
    resp = await async_client.post("/replays", json={"portfolio_id": str(portfolio.id), "period_key": "demo_stress_period"}, headers=auth_headers)
    assert resp.status_code == 202
    replay_id = resp.json()["id"]

    # 3. Check status
    resp = await async_client.get(f"/replays/{replay_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] in ["pending", "in_progress", "complete"]
