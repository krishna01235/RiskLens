"""
workers/regime_worker.py — Scheduled HMM Market Regime refit worker (F12).

Periodically fits a 2-state Gaussian HMM against a benchmark return series
to determine the probability that the market is in a "stressed" (high variance) state.
Writes the probability to a shared Redis key and audits to Postgres.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.ai.models  # noqa: F401
import app.alerts.models  # noqa: F401
import app.auth.models  # noqa: F401
import app.replays.models  # noqa: F401
import app.simulations.models  # noqa: F401
import app.portfolios.models  # noqa: F401
import app.risk.models  # noqa: F401
from app.risk.models import RegimeState
from quant.regime import fit_hmm, forward_probability

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("regime_worker")

REFIT_INTERVAL_SECONDS = 5 * 60  # 5 minutes
_PRICE_HISTORY_PREFIX = "price_history:"
_MARKET_REGIME_KEY = "market:regime_probability"

def _load_settings() -> tuple[str, str]:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL missing.")
        sys.exit(1)
    return redis_url, db_url

async def fetch_market_returns(redis: Redis) -> np.ndarray | None:
    """
    Constructs an equal-weighted benchmark return series from all available symbols
    in the price history cache.
    """
    keys = await redis.keys(f"{_PRICE_HISTORY_PREFIX}*")
    if not keys:
        return None

    all_returns = []
    
    for key in keys:
        closes_dict = await redis.hgetall(key)
        if not closes_dict:
            continue
        
        series = pd.Series({d: float(v) for d, v in closes_dict.items()}).sort_index()
        if len(series) < 2:
            continue
            
        returns = np.log(series / series.shift(1)).dropna()
        all_returns.append(returns)
        
    if not all_returns:
        return None
        
    # Align by date and take cross-sectional mean
    df = pd.concat(all_returns, axis=1)
    # Fill NAs if some assets started trading later (for simplicity, we can just drop or mean over non-NAs)
    mean_returns = df.mean(axis=1, skipna=True).dropna()
    
    # We need enough data to fit an HMM reliably
    if len(mean_returns) < 50:
        return None
        
    return mean_returns.values

async def refit_regime(db: AsyncSession, redis: Redis) -> None:
    try:
        returns = await fetch_market_returns(redis)
        if returns is None:
            logger.debug("Insufficient market data to fit regime model")
            return
            
        model = fit_hmm(returns)
        prob_stressed = forward_probability(model, returns)
        prob_calm = 1.0 - prob_stressed
        
        now = datetime.now(UTC)
        
        # Write to Redis
        payload = {
            "stressed_probability": prob_stressed,
            "calm_probability": prob_calm,
            "updated_at": now.timestamp()
        }
        await redis.set(_MARKET_REGIME_KEY, json.dumps(payload))
        
        # Write to Postgres
        state_record = RegimeState(
            calm_probability=Decimal(str(round(prob_calm, 4))),
            stressed_probability=Decimal(str(round(prob_stressed, 4))),
            captured_at=now
        )
        db.add(state_record)
        await db.commit()
        
        logger.info(f"Refit market regime: stressed_prob={prob_stressed:.4f}")
        
    except Exception:
        logger.exception("Failed to refit market regime")

async def run_regime_worker() -> None:
    redis_url, db_url = _load_settings()
    redis = Redis.from_url(redis_url, decode_responses=True)
    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Starting regime worker loop...")

    while True:
        try:
            async with session_factory() as db:
                await refit_regime(db, redis)
        except Exception as exc:
            logger.error("Error in regime worker loop: %s", exc, exc_info=True)
        
        await asyncio.sleep(REFIT_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_regime_worker())
    except KeyboardInterrupt:
        logger.info("Regime worker shut down.")
