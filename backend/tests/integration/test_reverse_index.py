import asyncio
import uuid
import json
import pytest
from redis.asyncio import Redis
from sqlalchemy import select
from app.config import get_settings
from app.database import async_session_factory
from app.portfolios.reverse_index_service import update_symbol_index
from app.risk.models import SymbolSubscription

@pytest.mark.asyncio
async def test_reverse_index_pubsub_flow():
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    
    # 1. Start listening to market:control
    pubsub = redis.pubsub()
    await pubsub.subscribe("market:control")
    
    # Wait for subscription to be established
    await asyncio.sleep(0.2)
    
    symbol = f"TEST_{uuid.uuid4().hex[:6].upper()}"
    portfolio_id = uuid.uuid4()
    
    async with async_session_factory() as db:
        try:
            # 2. Add holding -> transition 0 to 1
            await update_symbol_index(db, redis, symbol, portfolio_id, 1)
            
            # 3. Verify Redis pubsub received "subscribe"
            msg = None
            for _ in range(10):
                msg = await pubsub.get_message(ignore_subscribe_messages=True)
                if msg is not None:
                    break
                await asyncio.sleep(0.1)
            
            assert msg is not None
            data = json.loads(msg["data"])
            assert data["action"] == "subscribe"
            assert data["symbol"] == symbol
            
            # 4. Verify DB row
            res = await db.execute(select(SymbolSubscription).where(SymbolSubscription.symbol == symbol))
            sub = res.scalar_one_or_none()
            assert sub is not None
            assert sub.subscriber_count == 1
            
            # 5. Remove holding -> transition 1 to 0
            await update_symbol_index(db, redis, symbol, portfolio_id, -1)
            
            # 6. Verify Redis pubsub received "unsubscribe"
            msg = None
            for _ in range(10):
                msg = await pubsub.get_message(ignore_subscribe_messages=True)
                if msg is not None:
                    break
                await asyncio.sleep(0.1)
                
            assert msg is not None
            data = json.loads(msg["data"])
            assert data["action"] == "unsubscribe"
            assert data["symbol"] == symbol
            
            # 7. Verify DB row is 0
            res = await db.execute(select(SymbolSubscription).where(SymbolSubscription.symbol == symbol))
            sub = res.scalar_one_or_none()
            assert sub is not None
            assert sub.subscriber_count == 0
            
        finally:
            # Cleanup
            await redis.delete(f"reverse_index:{symbol}")
            await redis.delete(f"subscriber_count:{symbol}")
            
            # Note: the test DB is usually wiped, but if not we could delete the row.
            res = await db.execute(select(SymbolSubscription).where(SymbolSubscription.symbol == symbol))
            sub = res.scalar_one_or_none()
            if sub:
                await db.delete(sub)
                await db.commit()
                
            await pubsub.unsubscribe("market:control")
            await pubsub.aclose()
            await redis.aclose()
