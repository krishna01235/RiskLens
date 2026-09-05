"""tests/unit/test_simulations_service.py — Unit tests for simulations service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.engine import Result

from app.portfolios.models import Portfolio
from app.simulations.models import Simulation
from app.simulations.schemas import SimulationCreateRequest, SimulationResultPayload
from app.simulations.service import (
    create_simulation,
    get_simulation,
    mark_running,
    mark_complete,
    mark_failed,
    _assert_portfolio_owned,
    _check_rate_limits
)

@pytest.fixture
def db_mock():
    return AsyncMock()

@pytest.mark.asyncio
async def test_assert_portfolio_owned_success(db_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: portfolio)
    
    await _assert_portfolio_owned(db_mock, portfolio.id, user_id) # Should not raise

@pytest.mark.asyncio
async def test_assert_portfolio_owned_failure(db_mock):
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
    
    with pytest.raises(HTTPException) as exc:
        await _assert_portfolio_owned(db_mock, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_check_rate_limits_hourly_exceeded(db_mock):
    # First query is hourly count, second is concurrent count
    db_mock.execute.side_effect = [
        MagicMock(scalar_one=lambda: 10), # Max is 10
    ]
    with pytest.raises(HTTPException) as exc:
        await _check_rate_limits(db_mock, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 429

@pytest.mark.asyncio
async def test_check_rate_limits_concurrent_exceeded(db_mock):
    db_mock.execute.side_effect = [
        MagicMock(scalar_one=lambda: 5), # Hourly count
        MagicMock(scalar_one=lambda: 1), # Concurrent count (max is 1)
    ]
    with pytest.raises(HTTPException) as exc:
        await _check_rate_limits(db_mock, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_create_simulation_success(db_mock):
    user_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    # _assert_portfolio_owned
    # _check_rate_limits (2 queries)
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one=lambda: 0),
        MagicMock(scalar_one=lambda: 0),
    ]
    
    req = SimulationCreateRequest(portfolio_id=portfolio_id, horizon_days=30, num_paths=1000)
    sim = await create_simulation(db_mock, req, user_id)
    
    assert sim.status == "pending"
    assert db_mock.add.called
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_get_simulation_success(db_mock):
    user_id = uuid.uuid4()
    sim = Simulation(id=uuid.uuid4())
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: sim)
    
    res = await get_simulation(db_mock, sim.id, user_id)
    assert res == sim

@pytest.mark.asyncio
async def test_mark_running(db_mock):
    sim = Simulation(id=uuid.uuid4(), status="pending")
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: sim)
    
    await mark_running(db_mock, sim.id)
    assert sim.status == "running"
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_mark_complete(db_mock):
    sim = Simulation(id=uuid.uuid4(), status="running")
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: sim)
    
    results = SimulationResultPayload(
        portfolio_value=1000.0,
        expected_shortfall=100.0,
        var_95=80.0,
        paths=[]
    )
    await mark_complete(db_mock, sim.id, results)
    
    assert sim.status == "complete"
    assert "portfolio_value" in sim.results
    assert sim.completed_at is not None
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_mark_failed(db_mock):
    sim = Simulation(id=uuid.uuid4(), status="running")
    db_mock.execute.return_value = MagicMock(scalar_one_or_none=lambda: sim)
    
    await mark_failed(db_mock, sim.id, "Error occurred")
    
    assert sim.status == "failed"
    assert sim.error_message == "Error occurred"
    assert sim.completed_at is not None
    assert db_mock.commit.called
