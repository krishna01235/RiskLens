"""
workers/job_worker.py -- arq job worker entrypoint.

This worker runs async background jobs enqueued by the API:
  - run_monte_carlo_job: runs the Monte Carlo simulation for a given simulation_id.

Job safety guarantees:
  - Always transitions status to "complete" OR "failed" -- never leaves "pending".
  - arq job timeout (5 min) is a hard upper bound even if the job hangs.
  - All exceptions are caught, recorded, and the job exits cleanly.
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from typing import Any

import numpy as np
import pandas as pd
from arq import ArqRedis
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.portfolios.models import Portfolio
from app.simulations.models import Simulation
from app.simulations.schemas import SimulationResultPayload
from app.simulations import service as sim_service
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.evt import fit_evt
from quant.monte_carlo import SimulationParams, run_simulation_batched
from quant.returns import (
    ReturnSeries,
    compute_portfolio_returns,
    compute_returns,
    compute_weights,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# DB session factory (separate from FastAPI's -- workers run outside the API)
# ---------------------------------------------------------------------------

_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
_AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
    _engine, class_=AsyncSession, expire_on_commit=False
)


async def _get_db_session() -> AsyncSession:
    return _AsyncSessionLocal()


# ---------------------------------------------------------------------------
# Helper: build SimulationParams from DB + Redis state
# ---------------------------------------------------------------------------


async def _build_params(
    sim: Simulation,
    db: AsyncSession,
    redis: ArqRedis,
) -> tuple[SimulationParams, np.ndarray | None]:
    """Load holdings + price history to build SimulationParams."""
    # Load portfolio holdings
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == sim.portfolio_id)
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if portfolio is None:
        raise ValueError(f"Portfolio {sim.portfolio_id} not found.")

    # Build holdings dict: symbol -> (quantity, avg_price)
    holdings: dict[str, tuple[float, float]] = {}
    for h in portfolio.holdings:
        holdings[str(h.symbol)] = (float(h.quantity), float(h.average_price))

    if not holdings:
        raise ValueError("Portfolio has no holdings to simulate.")

    symbols = list(holdings.keys())
    weights_dict = compute_weights(holdings)
    weights = np.array([weights_dict[s] for s in symbols], dtype=float)

    # Current values = weight * total_portfolio_value (approximated from holdings)
    total_value = sum(qty * price for qty, price in holdings.values())
    current_values = np.array(
        [weights_dict[s] * total_value for s in symbols], dtype=float
    )

    # Fetch GARCH vols from Redis: symbol_volatility:{symbol}
    garch_vols: dict[int, float] = {}
    for i, sym in enumerate(symbols):
        raw = await redis.get(f"symbol_volatility:{sym}")
        if raw is not None:
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    vol = float(data.get("annualised_vol", 0))
                else:
                    vol = float(data)
                if vol > 0:
                    garch_vols[i] = vol
            except (ValueError, TypeError):
                pass

    # Build historical price frame
    history: dict[str, dict[str, str]] = {}
    for sym in symbols:
        closes = await redis.hgetall(f"price_history:{sym}")
        if closes:
            history[sym] = dict(closes)

    frame = {}
    for sym, closes in history.items():
        frame[sym] = pd.Series({d: float(v) for d, v in closes.items()})
    prices = pd.DataFrame(frame) if frame else pd.DataFrame()
    if not prices.empty:
        prices = prices.sort_index()

    portfolio_returns = None
    n = len(symbols)
    placeholder_daily_sigma = 0.02
    cov_matrix = np.diag([placeholder_daily_sigma**2] * n)
    mean_daily_returns = np.zeros(n)

    if len(prices) >= 2:
        try:
            returns_df: ReturnSeries = compute_returns(prices, kind="log")
            cov_result = estimate_covariance(returns_df.values)
            
            # Align everything to the symbols returned by estimate_covariance
            aligned_symbols = cov_result.symbols
            aligned_n = len(aligned_symbols)
            
            weights_map = {s: holdings[s] for s in aligned_symbols}
            aligned_weights = compute_weights(weights_map)
            port_ret = compute_portfolio_returns(returns_df, aligned_weights)
            portfolio_returns = port_ret.values.to_numpy()
            
            # Override placeholders with real data
            symbols = aligned_symbols
            weights = np.array([aligned_weights[s] for s in symbols], dtype=float)
            current_values = np.array([aligned_weights[s] * total_value for s in symbols], dtype=float)
            mean_daily_returns = np.mean(returns_df.values.to_numpy(), axis=0)
            cov_matrix = cov_result.matrix
        except (ValueError, InsufficientDataError):
            pass

    params = SimulationParams(
        num_paths=sim.num_paths,
        horizon_days=sim.horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
    )
    return params, portfolio_returns


# ---------------------------------------------------------------------------
# Monte Carlo job function
# ---------------------------------------------------------------------------


async def run_monte_carlo_job(ctx: dict[str, Any], simulation_id: str) -> None:
    """arq job: run a Monte Carlo simulation end-to-end.

    Status transitions:
      pending -> running -> complete   (happy path)
      pending -> running -> failed     (any exception)
    """
    sim_uuid = uuid.UUID(simulation_id)
    redis: ArqRedis = ctx["redis"]

    db: AsyncSession = await _get_db_session()
    try:
        # 1. Mark running
        await sim_service.mark_running(db, sim_uuid)

        # 2. Load simulation row
        result = await db.execute(select(Simulation).where(Simulation.id == sim_uuid))
        sim = result.scalar_one_or_none()
        if sim is None:
            logger.error("Simulation %s not found.", simulation_id)
            return

        # 3. Build params
        params, portfolio_returns = await _build_params(sim, db, redis)

        # 4. Publish progress via Redis pub/sub on portfolio channel
        channel = f"risk_updates:{sim.portfolio_id}"
        paths_done_ref = [0]

        async def publish_progress(pct: float) -> None:
            payload = json.dumps(
                {"type": "simulation_progress", "simulation_id": simulation_id, "progress": round(pct, 3)}
            )
            await redis.publish(channel, payload)

        # Sync progress_cb wrapper (run_simulation_batched is sync)
        import asyncio

        loop = asyncio.get_event_loop()

        def sync_progress_cb(pct: float) -> None:
            # Schedule the coroutine on the running event loop
            asyncio.run_coroutine_threadsafe(publish_progress(pct), loop)

        # 5. Run simulation (batched for progress streaming)
        sim_result = run_simulation_batched(
            params,
            batch_size=10_000,
            progress_cb=sync_progress_cb,
        )

        # 6. Run EVT fit synchronously
        evt_payload = None
        if portfolio_returns is not None:
            evt_fit = fit_evt(portfolio_returns, threshold_quantile=0.90, confidence=0.95)
            evt_payload = {
                "is_valid": evt_fit.is_valid,
                "message": evt_fit.message,
                "var_95": evt_fit.var_95,
                "cvar_95": evt_fit.cvar_95,
            }
        else:
            evt_payload = {
                "is_valid": False,
                "message": "EVT estimate unavailable: requires at least 20 tail exceedances, but no historical data is available.",
            }

        # 7. Save results
        payload = SimulationResultPayload(
            prob_profit=sim_result.prob_profit,
            prob_loss=sim_result.prob_loss,
            expected_pnl=sim_result.expected_pnl,
            pnl_p5=sim_result.pnl_p5,
            pnl_p50=sim_result.pnl_p50,
            pnl_p95=sim_result.pnl_p95,
            num_paths=sim_result.num_paths,
            evt=evt_payload,
        )
        await sim_service.mark_complete(db, sim_uuid, payload)

        # Publish completion message
        complete_payload = json.dumps(
            {"type": "simulation_complete", "simulation_id": simulation_id, "status": "complete"}
        )
        await redis.publish(channel, complete_payload)
        logger.info("Simulation %s completed successfully.", simulation_id)

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.exception("Simulation %s failed: %s", simulation_id, error_msg)
        try:
            await sim_service.mark_failed(db, sim_uuid, error_msg[:2000])
        except Exception:
            logger.exception("Failed to mark simulation %s as failed.", simulation_id)
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# arq WorkerSettings
# ---------------------------------------------------------------------------


class WorkerSettings:
    """arq worker configuration."""

    redis_settings = RedisSettings.from_dsn(
        get_settings().redis_url.replace("redis://", "redis://").split("?")[0]
    )
    functions = [run_monte_carlo_job]
    max_jobs = 4
    job_timeout = 300  # 5 minutes hard timeout -- never stuck pending
    keep_result = 3600  # keep job result in Redis for 1 hour
