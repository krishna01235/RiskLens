"""workers/ingestion_worker.py — Market Data Ingestion via Finnhub WS."""

import asyncio
import contextlib
import json
import logging
import os
import sys

import websockets
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ingestion_worker")

# Shared state to track current active subscriptions across reconnects
active_subscriptions = set()

async def get_initial_subscriptions() -> set[str]:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL missing, defaulting to empty subscription set")
        return set()
    
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine)
    
    subs = set()
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT symbol FROM symbol_subscriptions WHERE subscriber_count > 0"))
            for row in result:
                subs.add(row[0])
    except Exception as e:
        logger.error(f"Failed to load initial subscriptions: {e}")
    finally:
        await engine.dispose()
        
    return subs


async def control_channel_listener(redis: Redis, ws: websockets.WebSocketClientProtocol) -> None:
    """Listen for pub/sub control messages to dynamically subscribe/unsubscribe."""
    pubsub = redis.pubsub()
    await pubsub.subscribe("market:control")
    logger.info("Subscribed to market:control channel")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    action = data.get("action")
                    symbol = data.get("symbol")
                    
                    if symbol:
                        if action == "subscribe":
                            active_subscriptions.add(symbol)
                            await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                            logger.info(f"Dynamically subscribed to {symbol}")
                        elif action == "unsubscribe":
                            active_subscriptions.discard(symbol)
                            await ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
                            logger.info(f"Dynamically unsubscribed from {symbol}")
                except Exception as e:
                    logger.error(f"Error processing control message: {e}")
    except asyncio.CancelledError:
        logger.info("Control channel listener cancelled")
    finally:
        await pubsub.unsubscribe("market:control")
        await pubsub.close()


async def run_ingestion() -> None:
    finnhub_api_key = os.environ.get("FINNHUB_API_KEY")
    if not finnhub_api_key:
        logger.error("FINNHUB_API_KEY environment variable is missing. Exiting.")
        sys.exit(1)

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    ws_url = f"wss://ws.finnhub.io?token={finnhub_api_key}"
    
    global active_subscriptions
    active_subscriptions = await get_initial_subscriptions()
    logger.info(f"Loaded {len(active_subscriptions)} initial subscriptions")
    
    attempt = 0
    while True:
        try:
            logger.info(f"Connecting to Finnhub WebSocket (attempt {attempt})...")
            async with websockets.connect(ws_url) as ws:
                logger.info("Connected to Finnhub.")
                attempt = 0  # reset backoff on successful connection
                
                # Resubscribe to known active symbols
                for symbol in active_subscriptions:
                    await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                    logger.info(f"Resubscribed to {symbol}")

                # Start the control listener task
                listener_task = asyncio.create_task(control_channel_listener(redis, ws))

                try:
                    async for message in ws:
                        data = json.loads(message)
                        
                        if data.get("type") == "ping":
                            continue
                            
                        if data.get("type") == "trade":
                            for trade in data.get("data", []):
                                symbol = trade.get("s")
                                price = trade.get("p")
                                timestamp = trade.get("t")
                                
                                if symbol and price and timestamp:
                                    await redis.xadd(
                                        "market:ticks",
                                        {
                                            "symbol": str(symbol),
                                            "price": str(price),
                                            "timestamp": str(timestamp),
                                        },
                                        maxlen=100000,
                                        approximate=True,
                                    )
                finally:
                    listener_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await listener_task

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error in ingestion worker: {e}", exc_info=True)
            
        # Exponential backoff: min(2^attempt, 60)
        backoff_delay = min(2 ** attempt, 60)
        logger.info(f"Reconnecting in {backoff_delay} seconds...")
        await asyncio.sleep(backoff_delay)
        attempt += 1


if __name__ == "__main__":
    try:
        asyncio.run(run_ingestion())
    except KeyboardInterrupt:
        logger.info("Ingestion worker shut down.")
