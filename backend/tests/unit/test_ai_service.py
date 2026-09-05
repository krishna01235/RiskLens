"""tests/unit/test_ai_service.py — Unit tests for AI service."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.engine import Result

from app.ai.models import AiConversation, AiMessage
from app.ai.schemas import ExplainResponse, WhatIfResponse, ScenarioResultOut
from app.ai.service import (
    run_explain,
    run_what_if,
    list_conversations,
    list_messages,
    _get_or_create_conversation,
    _fetch_portfolio_context,
    _fetch_risk_snapshot
)
from app.portfolios.models import Holding, Portfolio


@pytest.fixture
def db_mock():
    return AsyncMock()

@pytest.fixture
def redis_mock():
    return AsyncMock()

@pytest.mark.asyncio
async def test_get_or_create_conversation_existing(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    conv = AiConversation(id=conv_id, portfolio_id=portfolio_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: conv),
    ]
    
    res = await _get_or_create_conversation(db_mock, portfolio_id, user_id, conv_id)
    assert res == conv
    assert not db_mock.add.called

@pytest.mark.asyncio
async def test_get_or_create_conversation_new(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: None), # conv not found
    ]
    
    res = await _get_or_create_conversation(db_mock, portfolio_id, user_id, uuid.uuid4())
    assert res.portfolio_id == portfolio_id
    assert db_mock.add.called

@pytest.mark.asyncio
async def test_fetch_risk_snapshot_empty(redis_mock):
    portfolio_id = uuid.uuid4()
    redis_mock.hgetall.return_value = {}
    
    res = await _fetch_risk_snapshot(redis_mock, portfolio_id)
    assert res["data_status"] == "pending"

@pytest.mark.asyncio
async def test_fetch_portfolio_context(db_mock, redis_mock):
    portfolio_id = uuid.uuid4()
    holdings = [
        Holding(symbol="AAPL", quantity=10, average_price=100),
        Holding(symbol="MSFT", quantity=5, average_price=200)
    ]
    
    db_mock.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: holdings))
    
    redis_mock.lrange.side_effect = [
        [b"100", b"110", b"121"], # AAPL
        [b"200", b"220", b"242"]  # MSFT
    ]
    
    weights, returns_df, value = await _fetch_portfolio_context(db_mock, redis_mock, portfolio_id)
    assert value == 2000.0
    assert weights["AAPL"] == 0.5
    assert weights["MSFT"] == 0.5
    assert not returns_df.empty
    assert len(returns_df) == 2

@pytest.mark.asyncio
@patch("app.ai.service.run_explain_graph", new_callable=AsyncMock)
async def test_run_explain(explain_graph_mock, db_mock, redis_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalar_one_or_none=lambda: None), # new conv
    ]
    
    redis_mock.hgetall.return_value = {}
    explain_graph_mock.return_value = ("Here is the explanation.", False)
    
    res = await run_explain(db_mock, redis_mock, portfolio_id, user_id, None)
    
    assert res.narration == "Here is the explanation."
    assert not res.timeout
    assert db_mock.add.call_count == 3 # 1 conv + 2 messages
    assert db_mock.commit.called

@pytest.mark.asyncio
@patch("app.ai.service.run_what_if_graph", new_callable=AsyncMock)
async def test_run_what_if(what_if_graph_mock, db_mock, redis_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio), # conv port
        MagicMock(scalar_one_or_none=lambda: None), # new conv
        MagicMock(scalars=lambda: MagicMock(all=lambda: [])) # fetch context holdings
    ]
    
    scenario_result = {"portfolio_value": 1000, "expected_shortfall": 50, "var_95": 40}
    what_if_graph_mock.return_value = (
        json.dumps(scenario_result),
        "What if narration",
        False,
        False,
        ""
    )
    
    res = await run_what_if(db_mock, redis_mock, portfolio_id, user_id, "What if market crashes?", None)
    
    assert res.narration == "What if narration"
    assert res.scenario_result is not None
    assert res.scenario_result.portfolio_value == 1000
    assert db_mock.add.call_count == 3
    assert db_mock.commit.called

@pytest.mark.asyncio
async def test_list_conversations(db_mock):
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalars=lambda: MagicMock(all=lambda: [AiConversation(id=uuid.uuid4(), portfolio_id=portfolio_id)]))
    ]
    
    res = await list_conversations(db_mock, portfolio_id, user_id)
    assert len(res) == 1

@pytest.mark.asyncio
async def test_list_messages(db_mock):
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    conv = AiConversation(id=conv_id, portfolio_id=portfolio_id)
    portfolio = Portfolio(id=portfolio_id, user_id=user_id)
    
    db_mock.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: conv),
        MagicMock(scalar_one_or_none=lambda: portfolio),
        MagicMock(scalars=lambda: MagicMock(all=lambda: [AiMessage(id=uuid.uuid4(), conversation_id=conv_id)]))
    ]
    
    res = await list_messages(db_mock, conv_id, user_id)
    assert len(res) == 1
