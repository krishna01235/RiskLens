"""tests/unit/test_ingestion_worker.py — Unit tests for ingestion worker."""

import asyncio
import json
import logging
from unittest.mock import AsyncMock, patch

import pytest
from websockets.exceptions import ConnectionClosed

from workers.ingestion_worker import run_ingestion


class StopLoopException(Exception):
    pass


@pytest.mark.asyncio
async def test_ingestion_worker_reconnect_backoff(monkeypatch, caplog):
    """Test that the worker reconnects with exponential backoff on WS drop."""
    caplog.set_level(logging.INFO)
    
    # Mock environment variables
    monkeypatch.setenv("FINNHUB_API_KEY", "test_key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    mock_get_subs = AsyncMock(return_value={"AAPL"})
    monkeypatch.setattr("workers.ingestion_worker.get_initial_subscriptions", mock_get_subs)

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis_from_url = AsyncMock(return_value=mock_redis)
    monkeypatch.setattr("workers.ingestion_worker.Redis.from_url", mock_redis_from_url)

    # Mock websockets.connect
    # We want it to fail immediately twice, then the third time we stop the loop.
    mock_ws = AsyncMock()
    
    connect_calls = 0
    
    async def mock_connect(*args, **kwargs):
        nonlocal connect_calls
        connect_calls += 1
        raise ConnectionClosed(rcvd=None, sent=None)

    # Mock websockets connect context manager
    class MockWebsocketsConnect:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return await mock_connect()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("workers.ingestion_worker.websockets.connect", MockWebsocketsConnect)

    # Mock asyncio.sleep to track backoff and eventually break the infinite loop
    sleep_calls = []
    
    async def mock_sleep(delay):
        sleep_calls.append(delay)
        if len(sleep_calls) >= 3:
            raise StopLoopException("Stop the loop")

    monkeypatch.setattr("workers.ingestion_worker.asyncio.sleep", mock_sleep)

    with pytest.raises(StopLoopException):
        await run_ingestion()

    # The backoff should be 2^0 = 1, 2^1 = 2, 2^2 = 4
    assert sleep_calls == [1, 2, 4]
    assert connect_calls == 3


@pytest.mark.asyncio
async def test_ingestion_worker_processes_trades(monkeypatch):
    """Test that the worker parses trades and publishes to Redis."""
    monkeypatch.setenv("FINNHUB_API_KEY", "test_key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    mock_get_subs = AsyncMock(return_value={"AAPL", "MSFT"})
    monkeypatch.setattr("workers.ingestion_worker.get_initial_subscriptions", mock_get_subs)

    mock_redis = AsyncMock()
    monkeypatch.setattr("workers.ingestion_worker.Redis.from_url", lambda *a, **kw: mock_redis)

    # We want a successful connection that yields one trade message, then we stop the loop
    class MockWS:
        def __init__(self):
            self.messages = [
                json.dumps({"type": "ping"}),
                json.dumps({
                    "type": "trade",
                    "data": [
                        {"s": "AAPL", "p": 150.5, "t": 1600000000},
                        {"s": "MSFT", "p": 300.0, "t": 1600000001},
                    ]
                })
            ]
            
        async def send(self, msg):
            pass
            
        async def __aiter__(self):
            for msg in self.messages:
                yield msg
            # After yielding messages, stop the loop to prevent infinite retry in test
            raise StopLoopException("Done")

    class MockWebsocketsConnect:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return MockWS()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("workers.ingestion_worker.websockets.connect", MockWebsocketsConnect)
    
    # Make sleep raise StopLoopException to break the while loop
    async def mock_sleep_stop(*args, **kwargs):
        raise StopLoopException("Stop loop")

    monkeypatch.setattr("workers.ingestion_worker.asyncio.sleep", mock_sleep_stop)

    with pytest.raises(StopLoopException):
        await run_ingestion()

    # Verify Redis XADD was called correctly
    assert mock_redis.xadd.call_count == 2
    
    call1 = mock_redis.xadd.call_args_list[0]
    assert call1.args[0] == "market:ticks"
    assert call1.args[1] == {"symbol": "AAPL", "price": "150.5", "timestamp": "1600000000"}

    call2 = mock_redis.xadd.call_args_list[1]
    assert call2.args[1] == {"symbol": "MSFT", "price": "300.0", "timestamp": "1600000001"}
