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
# Import all models that Portfolio has string-referenced relationships to,
# so SQLAlchemy mapper can resolve them at initialization time.
import app.alerts.models  # noqa: F401 — registers Alert
import app.risk.models  # noqa: F401 — registers RiskSnapshot
import app.simulations.models as _sim_models  # noqa: F401 — registers Simulation
import app.replays.models  # noqa: F401 — registers Replay
import app.ai.models  # noqa: F401 — registers AiConversation
from app.portfolios.models import Portfolio
from app.simulations.models import Simulation
from app.simulations.schemas import SimulationResultPayload
from app.simulations import service as sim_service
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.evt import fit_evt
from quant.monte_carlo import SimulationParams, run_simulation_batched
from workers.replay_job import run_replay_job
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


from workers.utils import build_simulation_params

async def _build_params(
    sim: Simulation,
    db: AsyncSession,
    redis: ArqRedis,
) -> tuple[SimulationParams, np.ndarray | None]:
    """Load holdings + price history to build SimulationParams."""
    return await build_simulation_params(
        portfolio_id=str(sim.portfolio_id),
        num_paths=sim.num_paths,
        horizon_days=sim.horizon_days,
        db=db,
        redis=redis,
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
    functions = [run_monte_carlo_job, run_replay_job]
    max_jobs = 4
    job_timeout = 300  # 5 minutes hard timeout -- never stuck pending
    keep_result = 3600  # keep job result in Redis for 1 hour
