"""
workers/garch_worker.py — Scheduled per-symbol GARCH(1,1) refit worker (F7).

Periodically fits a GARCH model for every actively subscribed symbol, using the
price history accumulated by the slow_path_worker. Writes the resulting
volatility to a JSON payload in Redis and audits to Postgres.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import pandas as pd
import numpy as np

from app.risk.models import GarchFit, SymbolSubscription
from quant.garch import fit_garch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("garch_worker")

# Worker sleep interval between full portfolio runs
REFIT_INTERVAL_SECONDS = 15 * 60  # 15 minutes

_PRICE_HISTORY_PREFIX = "price_history:"
_SYMBOL_VOLATILITY_PREFIX = "symbol_volatility:"

def _load_settings() -> tuple[str, str]:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL missing.")
        sys.exit(1)
    return redis_url, db_url

async def refit_symbol(
    db: AsyncSession,
    redis: Redis,
    symbol: str,
) -> None:
    """
    Fetch history, fit GARCH, write to Redis and Postgres.
    Wrapped in isolation so one failure does not crash the loop.
    """
    try:
        # Reuse Phase 10's price history buffer
        closes_dict = await redis.hgetall(f"{_PRICE_HISTORY_PREFIX}{symbol}")
        if not closes_dict:
            logger.debug("No price history for %s, skipping GARCH fit", symbol)
            return

        # Sort by date
        series = pd.Series({d: float(v) for d, v in closes_dict.items()}).sort_index()
        if len(series) < 2:
            return

        # Compute log returns
        returns = np.log(series / series.shift(1)).dropna()

        # Fit
        result = fit_garch(returns)

        now = datetime.now(UTC)

        # Write to Redis as JSON
        payload = {
            "volatility": result.volatility,
            "source": "fallback" if result.is_fallback else "garch",
            "updated_at": now.timestamp()
        }
        await redis.set(f"{_SYMBOL_VOLATILITY_PREFIX}{symbol}", json.dumps(payload))

        # Write audit row to Postgres
        fit_record = GarchFit(
            symbol=symbol,
            omega=Decimal(str(result.omega)) if result.omega is not None else None,
            alpha=Decimal(str(result.alpha)) if result.alpha is not None else None,
            beta=Decimal(str(result.beta)) if result.beta is not None else None,
            fitted_at=now
        )
        db.add(fit_record)
        await db.commit()
        
        logger.info("Refit GARCH for %s: vol=%f, source=%s", symbol, result.volatility, payload["source"])

    except Exception:
        logger.exception("Failed to refit GARCH for symbol %s (isolated)", symbol)

async def run_garch_worker() -> None:
    redis_url, db_url = _load_settings()
    redis = Redis.from_url(redis_url, decode_responses=True)
    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Starting GARCH worker loop...")

    while True:
        try:
            async with session_factory() as db:
                # Find all active subscriptions
                result = await db.execute(
                    select(SymbolSubscription.symbol)
                    .where(SymbolSubscription.subscriber_count > 0)
                )
                symbols = result.scalars().all()

                for symbol in symbols:
                    await refit_symbol(db, redis, symbol)
                    
        except Exception as exc:
            logger.error("Error in GARCH worker loop: %s", exc, exc_info=True)
        
        await asyncio.sleep(REFIT_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_garch_worker())
    except KeyboardInterrupt:
        logger.info("GARCH worker shut down.")
