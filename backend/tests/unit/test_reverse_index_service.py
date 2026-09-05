import uuid
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.portfolios.reverse_index_service import update_symbol_index
import app.portfolios.models
import app.alerts.models
import app.auth.models
import app.simulations.models
import app.replays.models
import app.ai.models

@pytest.mark.asyncio
async def test_update_symbol_index_add_0_to_1():
    mock_db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_redis = AsyncMock()
    
    mock_redis.pipeline = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[1, 1])
    mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    pid = uuid.uuid4()
    
    await update_symbol_index(mock_db, mock_redis, "AAPL", pid, 1)
    
    mock_pipe.sadd.assert_called_once_with("reverse_index:AAPL", str(pid))
    mock_pipe.scard.assert_called_once_with("reverse_index:AAPL")
    mock_redis.set.assert_called_once_with("subscriber_count:AAPL", "1")
    
    # DB updates
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # PubSub publish for 0 -> 1
    mock_redis.publish.assert_called_once_with("market:control", json.dumps({"action": "subscribe", "symbol": "AAPL"}))

@pytest.mark.asyncio
async def test_update_symbol_index_add_1_to_2():
    mock_db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_redis = AsyncMock()
    
    mock_redis.pipeline = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[1, 2])
    mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
    
    # DB mock: return existing subscription
    mock_sub = MagicMock()
    mock_sub.subscriber_count = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_sub
    mock_db.execute.return_value = mock_result
    
    pid = uuid.uuid4()
    
    await update_symbol_index(mock_db, mock_redis, "AAPL", pid, 1)
    
    mock_redis.publish.assert_not_called() # No transition, shouldn't publish
    assert mock_sub.subscriber_count == 2
    mock_db.add.assert_not_called()

@pytest.mark.asyncio
async def test_update_symbol_index_remove_1_to_0():
    mock_db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    mock_redis = AsyncMock()
    
    mock_redis.pipeline = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[1, 0])
    mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
    
    # DB mock: return existing subscription
    mock_sub = MagicMock()
    mock_sub.subscriber_count = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_sub
    mock_db.execute.return_value = mock_result
    
    pid = uuid.uuid4()
    
    await update_symbol_index(mock_db, mock_redis, "AAPL", pid, -1)
    
    mock_pipe.srem.assert_called_once_with("reverse_index:AAPL", str(pid))
    
    # PubSub publish for 1 -> 0
    mock_redis.publish.assert_called_once_with("market:control", json.dumps({"action": "unsubscribe", "symbol": "AAPL"}))
