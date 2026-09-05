"""tests/unit/test_portfolios_service.py — Unit tests for portfolios/service.py"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.engine import Result

from app.portfolios.models import Portfolio, Holding
from app.portfolios.schemas import AddHoldingRequest, DemoMarket, CsvConfirmRequest
from app.portfolios.service import (
    create_demo_portfolio,
    get_user_portfolios,
    get_portfolio,
    add_holding,
    delete_holding,
    preview_csv,
    confirm_csv_import,
)

@pytest.fixture
def db_mock():
    return AsyncMock()

@pytest.fixture
def redis_mock():
    return AsyncMock()

@pytest.mark.asyncio
async def test_create_demo_portfolio_existing(db_mock, redis_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id, source="demo", name="Demo Portfolio (US)")
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = portfolio
    db_mock.execute.return_value = mock_result
    
    res = await create_demo_portfolio(db_mock, redis_mock, user_id, DemoMarket.us)
    assert res == portfolio
    assert not db_mock.add.called
    db_mock.refresh.assert_called_with(portfolio, ["holdings"])

@pytest.mark.asyncio
@patch("app.portfolios.service.update_symbol_index", new_callable=AsyncMock)
async def test_create_demo_portfolio_new(update_symbol_mock, db_mock, redis_mock):
    user_id = uuid.uuid4()
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result
    
    res = await create_demo_portfolio(db_mock, redis_mock, user_id, DemoMarket.us)
    assert res.user_id == user_id
    assert res.source == "demo"
    assert db_mock.add.call_count > 1  # 1 for portfolio, multiple for holdings
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_get_user_portfolios(db_mock):
    user_id = uuid.uuid4()
    portfolios = [Portfolio(), Portfolio()]
    mock_result = MagicMock(spec=Result)
    mock_result.scalars.return_value.all.return_value = portfolios
    db_mock.execute.return_value = mock_result
    
    res = await get_user_portfolios(db_mock, user_id)
    assert len(res) == 2

@pytest.mark.asyncio
async def test_get_portfolio_not_found(db_mock):
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc:
        await get_portfolio(db_mock, uuid.uuid4(), uuid.uuid4())
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_portfolio_access_denied(db_mock):
    portfolio = Portfolio(id=uuid.uuid4(), user_id=uuid.uuid4())
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = portfolio
    db_mock.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc:
        await get_portfolio(db_mock, portfolio.id, uuid.uuid4())
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_get_portfolio_success(db_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    mock_result = MagicMock(spec=Result)
    mock_result.scalar_one_or_none.return_value = portfolio
    db_mock.execute.return_value = mock_result
    
    res = await get_portfolio(db_mock, portfolio.id, user_id)
    assert res == portfolio
    db_mock.refresh.assert_called_with(portfolio, ["holdings"])

@pytest.mark.asyncio
@patch("app.portfolios.service.update_symbol_index", new_callable=AsyncMock)
async def test_add_holding_upsert(update_symbol_mock, db_mock, redis_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    holding = Holding(symbol="AAPL", quantity=Decimal("10"), average_price=Decimal("150"))
    
    # First execute is for _get_portfolio_owned
    mock_res_portfolio = MagicMock(spec=Result)
    mock_res_portfolio.scalar_one_or_none.return_value = portfolio
    
    # Second execute is for finding existing holding
    mock_res_holding = MagicMock(spec=Result)
    mock_res_holding.scalar_one_or_none.return_value = holding
    
    db_mock.execute.side_effect = [mock_res_portfolio, mock_res_holding]
    
    req = AddHoldingRequest(symbol="AAPL", quantity=Decimal("20"), average_price=Decimal("160"), currency="USD")
    res = await add_holding(db_mock, redis_mock, portfolio.id, user_id, req)
    
    assert res.quantity == Decimal("20")
    assert res.average_price == Decimal("160")
    db_mock.commit.assert_called_once()
    update_symbol_mock.assert_called_once()

@pytest.mark.asyncio
@patch("app.portfolios.service.update_symbol_index", new_callable=AsyncMock)
async def test_add_holding_new(update_symbol_mock, db_mock, redis_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    
    mock_res_portfolio = MagicMock(spec=Result)
    mock_res_portfolio.scalar_one_or_none.return_value = portfolio
    
    mock_res_holding = MagicMock(spec=Result)
    mock_res_holding.scalar_one_or_none.return_value = None
    
    db_mock.execute.side_effect = [mock_res_portfolio, mock_res_holding]
    
    req = AddHoldingRequest(symbol="AAPL", quantity=Decimal("20"), average_price=Decimal("160"), currency="USD")
    res = await add_holding(db_mock, redis_mock, portfolio.id, user_id, req)
    
    assert res.quantity == Decimal("20")
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()

@pytest.mark.asyncio
@patch("app.portfolios.service.update_symbol_index", new_callable=AsyncMock)
async def test_delete_holding_success(update_symbol_mock, db_mock, redis_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    holding = Holding(id=uuid.uuid4(), portfolio_id=portfolio.id, symbol="AAPL")
    
    mock_res_portfolio = MagicMock(spec=Result)
    mock_res_portfolio.scalar_one_or_none.return_value = portfolio
    
    mock_res_holding = MagicMock(spec=Result)
    mock_res_holding.scalar_one_or_none.return_value = holding
    
    db_mock.execute.side_effect = [mock_res_portfolio, mock_res_holding]
    
    await delete_holding(db_mock, redis_mock, portfolio.id, holding.id, user_id)
    
    db_mock.delete.assert_called_once_with(holding)
    db_mock.commit.assert_called_once()
    update_symbol_mock.assert_called_once_with(db_mock, redis_mock, "AAPL", portfolio.id, -1)

@pytest.mark.asyncio
async def test_delete_holding_not_found(db_mock, redis_mock):
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=uuid.uuid4(), user_id=user_id)
    
    mock_res_portfolio = MagicMock(spec=Result)
    mock_res_portfolio.scalar_one_or_none.return_value = portfolio
    
    mock_res_holding = MagicMock(spec=Result)
    mock_res_holding.scalar_one_or_none.return_value = None
    
    db_mock.execute.side_effect = [mock_res_portfolio, mock_res_holding]
    
    with pytest.raises(HTTPException) as exc:
        await delete_holding(db_mock, redis_mock, portfolio.id, uuid.uuid4(), user_id)
    assert exc.value.status_code == 404

def test_preview_csv_empty():
    with pytest.raises(HTTPException) as exc:
        preview_csv(b"")
    assert exc.value.status_code == 422

def test_preview_csv_valid():
    csv_bytes = b"Symbol,Qty,Price\nAAPL,10,150.0\n"
    res = preview_csv(csv_bytes)
    assert "Symbol" in res.headers
    assert res.suggested_mapping["symbol"] == "Symbol"

@pytest.mark.asyncio
@patch("app.portfolios.service.update_symbol_index", new_callable=AsyncMock)
async def test_confirm_csv_import_success(update_symbol_mock, db_mock, redis_mock):
    user_id = uuid.uuid4()
    req = CsvConfirmRequest(
        currency="USD",
        mapping={"symbol": "Symbol", "quantity": "Qty", "average_price": "Price"},
        rows=[{"Symbol": "AAPL", "Qty": "10", "Price": "150"}]
    )
    
    res = await confirm_csv_import(db_mock, redis_mock, user_id, req)
    assert res.user_id == user_id
    assert res.source == "csv"
    assert db_mock.add.call_count == 2 # 1 portfolio, 1 holding
    assert db_mock.commit.called
    update_symbol_mock.assert_called_once()

@pytest.mark.asyncio
async def test_confirm_csv_import_empty(db_mock, redis_mock):
    user_id = uuid.uuid4()
    req = CsvConfirmRequest(
        currency="USD",
        mapping={"symbol": "Symbol", "quantity": "Qty", "average_price": "Price"},
        rows=[]
    )
    
    with pytest.raises(HTTPException) as exc:
        await confirm_csv_import(db_mock, redis_mock, user_id, req)
    assert exc.value.status_code == 422
