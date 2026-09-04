"""workers/decision_engine_worker.py -- Generates decision candidates on breach.

NOTE: This module is purely advisory. There is no code path anywhere in the
system capable of executing a trade. It only generates recommendations for the
user to consider.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.alerts.models  # noqa: F401
from app.alerts.models import Alert, Decision
from app.alerts.decisions_service import generate_and_evaluate_candidates
from quant.risk_metrics import RiskContribution
from workers.utils import build_simulation_params

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("decision_engine_worker")


def _load_settings() -> tuple[str, str]:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL missing.")
        sys.exit(1)
    return redis_url, db_url


async def process_alert(
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    portfolio_id: str,
    alert_msg: dict,
) -> None:
    if alert_msg.get("type") != "alert" or alert_msg.get("to_state") != "BREACH":
        return

    logger.info("Generating decision candidates for breach on portfolio %s", portfolio_id)

    # We need the alert ID from the DB to link the decision.
    # The alert was just written by slow_path_worker. Let's fetch the latest alert.
    async with session_factory() as db:
        alert_result = await db.execute(
            select(Alert)
            .where(Alert.portfolio_id == uuid.UUID(portfolio_id))
            .order_by(Alert.fired_at.desc())
            .limit(1)
        )
        alert = alert_result.scalar_one_or_none()
        if not alert:
            logger.error("No alert found in DB for portfolio %s to attach decisions to", portfolio_id)
            return
            
        # Get risk contributions from cached risk state
        state_json = await redis.hget(f"risk_state:{portfolio_id}", "risk")
        if not state_json:
            logger.error("No risk state found for portfolio %s", portfolio_id)
            return
            
        risk_data = json.loads(state_json)
        if risk_data.get("data_status") != "ready":
            logger.error("Risk state not ready for portfolio %s", portfolio_id)
            return
            
        risk_contributions_raw = risk_data.get("risk_contributions", [])
        risk_contributions = [
            RiskContribution(
                symbol=rc["symbol"],
                weight=rc["weight"],
                mcr=rc["mcr"],
                rc=rc["rc"],
                rc_pct=rc["rc_pct"]
            )
            for rc in risk_contributions_raw
        ]

        # Reuse identical covariance/volatility inputs as Monte Carlo (Phase 12)
        params, _ = await build_simulation_params(
            portfolio_id=portfolio_id,
            num_paths=10_000,
            horizon_days=30,  # 30 day horizon for decision evaluation
            db=db,
            redis=redis,
        )

        candidates = await generate_and_evaluate_candidates(
            horizon_days=params.horizon_days,
            weights=params.weights,
            current_values=params.current_values,
            mean_daily_returns=params.mean_daily_returns,
            cov_matrix=params.cov_matrix,
            garch_vols=params.garch_vols,
            symbols=params.symbols,
            risk_contributions=risk_contributions,
        )

        candidates_dicts = [
            {
                "label": c.label,
                "expected_return": c.expected_return,
                "cvar": c.cvar,
                "p_loss": c.p_loss,
                "score": c.score,
                "is_fallback": c.is_fallback,
            }
            for c in candidates
        ]

        decision = Decision(
            alert_id=alert.id,
            candidates=candidates_dicts,
            created_at=datetime.now(UTC),
        )
        db.add(decision)
        await db.commit()
        await db.refresh(decision)

    payload = json.dumps({
        "type": "decision_update",
        "portfolio_id": portfolio_id,
        "decision_id": str(decision.id),
        "alert_id": str(alert.id),
        "candidates": candidates_dicts,
        "created_at": decision.created_at.isoformat(),
    })
    await redis.publish(f"risk_updates:{portfolio_id}", payload)
    logger.info("Published decision update for portfolio %s", portfolio_id)


async def run_decision_engine() -> None:
    redis_url, db_url = _load_settings()
    redis = Redis.from_url(redis_url, decode_responses=True)
    
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Starting decision engine worker...")
    
    pubsub = redis.pubsub()
    await pubsub.psubscribe("risk_updates:*")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                try:
                    data = json.loads(message["data"])
                    portfolio_id = data.get("portfolio_id")
                    if portfolio_id and data.get("type") == "alert":
                        # Spawn async task to not block the pubsub listener
                        asyncio.create_task(process_alert(redis, session_factory, portfolio_id, data))
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    logger.error("Failed to process message: %s", e, exc_info=True)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe("risk_updates:*")
        await pubsub.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_decision_engine())
    except KeyboardInterrupt:
        logger.info("Decision engine worker shut down.")
