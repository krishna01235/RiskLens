"""tests/integration/test_ingestion.py — Integration tests for ingestion worker.

Requires Redis to be running.
"""

import asyncio

import pytest
from redis.asyncio import Redis

from app.config import get_settings


@pytest.mark.asyncio
async def test_redis_stream_publish():
    """Smoke test: manually publish to market:ticks and read it back."""
    settings = get_settings()
    
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    
    # Generate a unique stream name for the test to avoid clashing with real data
    stream_name = "test_market:ticks"
    
    # 1. Publish a tick
    msg_id = await redis.xadd(
        stream_name,
        {
            "symbol": "TEST",
            "price": "123.45",
            "timestamp": "1600000000",
        }
    )
    assert msg_id is not None
    
    # 2. Read it back
    messages = await redis.xread({stream_name: "0-0"}, count=1)
    
    assert len(messages) == 1
    stream, entries = messages[0]
    assert stream == stream_name
    assert len(entries) == 1
    
    entry_id, fields = entries[0]
    assert entry_id == msg_id
    assert fields["symbol"] == "TEST"
    assert fields["price"] == "123.45"
    
    # Clean up
    await redis.delete(stream_name)
    await redis.aclose()
