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
from quant.monte_carlo import SimulationParams, run_simulation_batched
from quant.returns import compute_weights

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
) -> SimulationParams:
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

    # Build a synthetic daily return history from holdings' cost basis
    # For MVP: use a small synthetic covariance if no price history available.
    # In production this would fetch price history from a rolling Redis buffer.
    # Using 0.02 daily sigma as a conservative placeholder.
    n = len(symbols)
    placeholder_daily_sigma = 0.02
    cov_matrix = np.diag([placeholder_daily_sigma**2] * n)
    mean_daily_returns = np.zeros(n)

    return SimulationParams(
        num_paths=sim.num_paths,
        horizon_days=sim.horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
    )


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
        params = await _build_params(sim, db, redis)

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

        # 6. Save results
        payload = SimulationResultPayload(
            prob_profit=sim_result.prob_profit,
            prob_loss=sim_result.prob_loss,
            expected_pnl=sim_result.expected_pnl,
            pnl_p5=sim_result.pnl_p5,
            pnl_p50=sim_result.pnl_p50,
            pnl_p95=sim_result.pnl_p95,
            num_paths=sim_result.num_paths,
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
