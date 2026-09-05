"""tests/unit/test_alerts_service.py — Unit tests for alerts service."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.engine import Result

from app.alerts.models import Alert, Decision
from app.alerts.schemas import RiskBudgetUpsertRequest
from app.portfolios.models import Portfolio, RiskBudget
from app.alerts.service import (
    upsert_risk_budget,
    get_risk_budget,
    get_alerts,
    get_latest_decision,
    _assert_portfolio_owned
)

@pytest.fixture
def db_mock():
    return AsyncMock()

@pytest.mark.asyncio
async def test_assert_portfolio_owned_success(db_mock):
    portfolio = Portfolio(id=uuid.uuid4(), user_id=uuid.uuid4())
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: portfolio)
    await _assert_portfolio_owned(db_mock, portfolio.id, portfolio.user_id)

@pytest.mark.asyncio
async def test_assert_portfolio_owned_not_found(db_mock):
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
    with pytest.raises(HTTPException) as exc:
        await _assert_portfolio_owned(db_mock, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_risk_budget_new(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio), # ownership
        MagicMock(scalar_one_or_none=lambda: None), # budget not found
    ]
    
    req = RiskBudgetUpsertRequest(max_cvar=10.0, watch_threshold=0.5, high_threshold=0.8, breach_threshold=0.9)
    budget = await upsert_risk_budget(db_mock, portfolio_id, user_id, req)
    
    assert budget.max_cvar == Decimal("10.0")
    assert db_mock.add.called
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_upsert_risk_budget_existing(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    budget = RiskBudget(portfolio_id=portfolio_id, max_cvar=Decimal("5.0"))
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: budget),
    ]
    
    req = RiskBudgetUpsertRequest(max_cvar=15.0, watch_threshold=0.6, high_threshold=0.7, breach_threshold=0.8)
    res = await upsert_risk_budget(db_mock, portfolio_id, user_id, req)
    
    assert res.max_cvar == Decimal("15.0")
    assert not db_mock.add.called
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_get_risk_budget(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    budget = RiskBudget(portfolio_id=portfolio_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: budget),
    ]
    
    res = await get_risk_budget(db_mock, portfolio_id, user_id)
    assert res == budget

@pytest.mark.asyncio
async def test_get_alerts(db_mock):
    user_id = uuid.uuid4()
    alerts = [Alert(id=uuid.uuid4()), Alert(id=uuid.uuid4())]
    
    db_mock.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: alerts))
    
    res = await get_alerts(db_mock, user_id, limit=2)
    assert len(res) == 2

@pytest.mark.asyncio
async def test_get_latest_decision(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    decision = Decision(id=uuid.uuid4())
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: decision),
    ]
    
    res = await get_latest_decision(db_mock, portfolio_id, user_id)
    assert res == decision
