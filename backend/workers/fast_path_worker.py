"""workers/fast_path_worker.py — Fast-path risk tick consumer."""

import asyncio
import json
import logging
import os
import sys
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("fast_path_worker")

# In-memory cache of holdings to avoid DB hits on the fast path.
# format: { portfolio_id_str: { symbol_str: {"quantity": Decimal, "average_price": Decimal} } }
HOLDINGS_CACHE = {}

# Keep track of latest known prices for all symbols
LATEST_PRICES = {}

async def load_holdings(session, portfolio_id: str):
    """Load holdings for a portfolio and update the cache."""
    try:
        query = text("SELECT symbol, quantity, average_price FROM holdings WHERE portfolio_id = :pid")
        result = await session.execute(query, {"pid": portfolio_id})
        
        holdings = {}
        for row in result:
            sym, qty, avg_px = row[0], row[1], row[2]
            holdings[sym] = {
                "quantity": Decimal(str(qty)),
                "average_price": Decimal(str(avg_px))
            }
            
        HOLDINGS_CACHE[portfolio_id] = holdings
        return holdings
    except Exception as e:
        logger.error(f"Error loading holdings for {portfolio_id}: {e}")
        return None

async def run_fast_path() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL missing.")
        sys.exit(1)
        
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine)

    stream_name = "market:ticks"
    group_name = "fast_path_group"
    
    # Ensure consumer group exists
    try:
        await redis.xgroup_create(stream_name, group_name, id="0", mkstream=True)
        logger.info(f"Created consumer group {group_name}")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group {group_name} already exists")
        else:
            logger.error(f"Error creating consumer group: {e}")

    logger.info("Starting fast path consumer loop...")
    
    last_processed_timestamps = {}
    
    while True:
        try:
            # Read from stream
            messages = await redis.xreadgroup(group_name, "fast_path_worker_1", {stream_name: ">"}, count=50, block=2000)
            
            if not messages:
                continue
                
            for stream, msg_list in messages:
                for msg_id, data in msg_list:
                    symbol = data.get("symbol")
                    price_str = data.get("price")
                    timestamp_str = data.get("timestamp")
                    
                    if not symbol or not price_str or not timestamp_str:
                        await redis.xack(stream_name, group_name, msg_id)
                        continue
                        
                    price = Decimal(price_str)
                    timestamp = float(timestamp_str)
                    
                    # Idempotency check: drop if out of order
                    last_ts = last_processed_timestamps.get(symbol, 0)
                    if timestamp <= last_ts:
                        logger.debug(f"Dropping out of order or duplicate tick for {symbol}")
                        await redis.xack(stream_name, group_name, msg_id)
                        continue
                        
                    last_processed_timestamps[symbol] = timestamp
                    LATEST_PRICES[symbol] = price
                    
                    # Find affected portfolios
                    index_key = f"reverse_index:{symbol}"
                    affected_portfolios = await redis.smembers(index_key)
                    
                    for pid in affected_portfolios:
                        # Ensure we have holdings in cache
                        if pid not in HOLDINGS_CACHE:
                            async with async_session() as session:
                                await load_holdings(session, pid)
                                
                        holdings = HOLDINGS_CACHE.get(pid, {})
                        
                        portfolio_value = Decimal("0.0")
                        total_pnl = Decimal("0.0")
                        
                        # Recompute based on holdings and latest prices
                        for sym, details in holdings.items():
                            qty = details["quantity"]
                            avg_px = details["average_price"]
                            
                            current_price = LATEST_PRICES.get(sym, avg_px)  # Fallback to avg_px if no tick yet
                            
                            portfolio_value += qty * current_price
                            total_pnl += qty * (current_price - avg_px)
                            
                        # Format metrics
                        risk_state = {
                            "portfolio_value": str(portfolio_value),
                            "daily_pnl": str(total_pnl),
                            "timestamp": timestamp
                        }
                        
                        # Write to Redis and Publish
                        state_key = f"risk_state:{pid}"
                        channel_key = f"risk_updates:{pid}"
                        
                        await redis.hset(state_key, mapping=risk_state)
                        
                        # Also publish the event to websocket consumers
                        payload = json.dumps({
                            "type": "risk_update",
                            "portfolio_id": pid,
                            "portfolio_value": str(portfolio_value),
                            "daily_pnl": str(total_pnl),
                            "timestamp": timestamp
                        })
                        await redis.publish(channel_key, payload)
                    
                    # Acknowledge the message
                    await redis.xack(stream_name, group_name, msg_id)

        except Exception as e:
            logger.error(f"Error in fast path worker loop: {e}", exc_info=True)
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_fast_path())
    except KeyboardInterrupt:
        logger.info("Fast path worker shut down.")
