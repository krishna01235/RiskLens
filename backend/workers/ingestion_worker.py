"""workers/ingestion_worker.py — Market Data Ingestion via Finnhub WS."""

import asyncio
import json
import logging
import os
import sys

import websockets
from redis.asyncio import Redis
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ingestion_worker")

# We subscribe to a small fixed demo list to stay within Finnhub free tier limits
# and to guarantee ticks for testing.
DEMO_SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "BINANCE:BTCUSDT",  # crypto ensures we get ticks outside US market hours
]


async def run_ingestion() -> None:
    finnhub_api_key = os.environ.get("FINNHUB_API_KEY")
    if not finnhub_api_key:
        logger.error("FINNHUB_API_KEY environment variable is missing. Exiting.")
        sys.exit(1)

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url, decode_responses=True)

    ws_url = f"wss://ws.finnhub.io?token={finnhub_api_key}"
    
    attempt = 0
    while True:
        try:
            logger.info(f"Connecting to Finnhub WebSocket (attempt {attempt})...")
            async with websockets.connect(ws_url) as ws:
                logger.info("Connected to Finnhub.")
                attempt = 0  # reset backoff on successful connection
                
                # Subscribe to demo symbols
                for symbol in DEMO_SYMBOLS:
                    await ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                    logger.info(f"Subscribed to {symbol}")

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
                                # Push to Redis Stream `market:ticks`
                                await redis.xadd(
                                    "market:ticks",
                                    {
                                        "symbol": str(symbol),
                                        "price": str(price),
                                        "timestamp": str(timestamp),
                                    },
                                    # Cap the stream size to 100,000 to prevent OOM
                                    maxlen=100000,
                                    approximate=True,
                                )
                                logger.debug(f"Tick: {symbol} @ {price}")

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
