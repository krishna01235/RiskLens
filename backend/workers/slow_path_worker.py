"""workers/slow_path_worker.py — Slow-path batched risk recompute worker (F5).

Consumes the same Redis Stream ``market:ticks`` as the fast path, but through
its *own* consumer group and on a *batched/debounced* cadence.  For each
rolling window it runs the Phase 8 quant engine over the assembled daily price
history and writes the result into ``risk_state:{portfolio_id}`` (merged with
the fast-path hash fields), then publishes a ``risk_update`` WS message.

Design notes (Phase 10 spec):
- Batching: a window flushes when either WINDOW_TICKS ticks have been seen or
  WINDOW_SECONDS have elapsed since the first pending tick — whichever first.
- Price history: a per-symbol daily-close buffer is kept in Redis
  (``price_history:{symbol}`` hash of date -> close).  The first time a symbol
  is observed it is seeded from Finnhub's REST `/stock/candle` endpoint so a
  meaningful covariance matrix is available immediately (spec "Known Risks").
- Insufficient data: a portfolio with fewer than MIN_OBSERVATIONS aligned
  daily returns lands in an explicit ``insufficient_data`` state — never a
  silently-wrong number, never a crash (F5 edge case).
- Isolation: every portfolio recompute is wrapped in its own try/except; one
  failing portfolio must not stop the loop for the others (F5 Errors rule).
- Snapshots: every ~5 minutes per portfolio, a ``risk_snapshots`` row is
  persisted (append-only audit trail; risk_state/risk_contribution/
  correlation_flags stay placeholders until Phases 14/15).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import numpy as np
import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import the full ORM model graph so SQLAlchemy can resolve every relationship
# string (Portfolio -> Alert/Simulation/Replay/AiConversation/...) when this
# standalone worker first executes a query.  See tests/integration/conftest.py.
import app.ai.models  # noqa: F401
import app.alerts.models  # noqa: F401
import app.auth.models  # noqa: F401
import app.replays.models  # noqa: F401
import app.simulations.models  # noqa: F401
from app.alerts.models import Alert
from app.alerts.state_machine import AlertState, compute_state, should_fire_alert, utilization as compute_utilization
from app.portfolios.models import Holding, RiskBudget
from app.risk.models import RiskSnapshot
from quant.covariance import InsufficientDataError, estimate_covariance
from quant.returns import (
    ReturnSeries,
    compute_portfolio_returns,
    compute_returns,
    compute_weights,
)
from quant.risk_metrics import RiskEstimate, compute_risk_estimate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("slow_path_worker")

# ── Stream / group constants ──────────────────────────────────────────────────
STREAM_NAME = "market:ticks"
GROUP_NAME = "slow_path_group"
CONSUMER_NAME = "slow_path_worker_1"
BATCH_SIZE = 100
BLOCK_MS = 100

# ── Batching window (F5: "every 2 seconds or every 20 ticks") ─────────────────
WINDOW_TICKS = 20
WINDOW_SECONDS = 2.0

# ── Price history buffer ─────────────────────────────────────────────────────
HISTORY_CAP = 250  # max daily closes retained per symbol
BOOTSTRAP_DAYS = 60  # Finnhub REST bootstrap window for a newly-seen symbol

# ── Snapshot persistence interval (F5: ~5 minutes) ────────────────────────────
SNAPSHOT_INTERVAL_SECONDS = 5 * 60

_PRICE_HISTORY_PREFIX = "price_history:"
_RISK_STATE_PREFIX = "risk_state:"
_RISK_UPDATES_PREFIX = "risk_updates:"
_REVERSE_INDEX_PREFIX = "reverse_index:"
_FINNHUB_CANDLE_URL = "https://finnhub.io/api/v1/stock/candle"


class WindowBatcher:
    """Aggregates affected portfolios into a rolling recompute window.

    A flush is triggered by either threshold:
      - ``max_ticks`` processed ticks (count-based), or
      - ``max_seconds`` elapsed since the first pending tick (time-based),
    whichever comes first.  Pure and clock-injectable for unit testing.
    """

    def __init__(
        self, max_ticks: int = WINDOW_TICKS, max_seconds: float = WINDOW_SECONDS
    ) -> None:
        self.max_ticks = max_ticks
        self.max_seconds = max_seconds
        self._portfolio_ids: set[str] = set()
        self._tick_count = 0
        self._first_tick_at: float | None = None

    def add(self, portfolio_ids: set[str], now: float) -> None:
        """Record a processed tick affecting *portfolio_ids* at monotonic *now*."""
        if not portfolio_ids:
            return
        self._portfolio_ids.update(portfolio_ids)
        self._tick_count += 1
        if self._first_tick_at is None:
            self._first_tick_at = now

    def should_flush(self, now: float) -> bool:
        """Return True if the window is due for a flush at monotonic *now*."""
        if self._tick_count >= self.max_ticks:
            return True
        return (
            self._first_tick_at is not None
            and now - self._first_tick_at >= self.max_seconds
        )

    def drain(self) -> set[str]:
        """Return the accumulated portfolio ids and reset the window."""
        portfolios, self._portfolio_ids = self._portfolio_ids, set()
        self._tick_count = 0
        self._first_tick_at = None
        return portfolios


# ── Price history buffer ──────────────────────────────────────────────────────


async def record_tick(
    redis: Redis, symbol: str, price: str, timestamp_sec: float
) -> None:
    """Upsert today's close for *symbol* and prune the buffer to HISTORY_CAP."""
    day = datetime.fromtimestamp(timestamp_sec, tz=UTC).date().isoformat()
    key = f"{_PRICE_HISTORY_PREFIX}{symbol}"

    await redis.hset(key, day, str(price))

    fields = await redis.hkeys(key)
    if len(fields) > HISTORY_CAP:
        # Hash keys are ISO dates, so lexicographic order == chronological order.
        to_remove = sorted(fields)[: len(fields) - HISTORY_CAP]
        if to_remove:
            await redis.hdel(key, *to_remove)


async def seed_price_history(
    redis: Redis,
    symbol: str,
    finnhub_api_key: str,
    seeded: set[str],
) -> None:
    """Bootstrap *symbol*'s daily-close buffer from Finnhub REST candles (once).

    Best-effort: a missing/empty API key or a failed call simply leaves the
    buffer empty — the portfolio will surface ``insufficient_data`` until
    enough ticks accumulate, which is the explicit F5 edge-case state.
    """
    if symbol in seeded:
        return
    seeded.add(symbol)  # never retry-spam the REST endpoint within a run

    if not finnhub_api_key:
        logger.info("No FINNHUB_API_KEY set; skipping REST bootstrap for %s", symbol)
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _FINNHUB_CANDLE_URL,
                params={
                    "symbol": symbol,
                    "resolution": "D",
                    "count": BOOTSTRAP_DAYS,
                    "token": finnhub_api_key,
                },
            )
        if resp.status_code != 200:
            logger.warning(
                "Finnhub candle bootstrap for %s returned %s", symbol, resp.status_code
            )
            return
        data = resp.json()
        if data.get("s") != "ok":
            logger.warning(
                "Finnhub candle bootstrap for %s: status=%s", symbol, data.get("s")
            )
            return

        times = data.get("t") or []
        closes = data.get("c") or []
        if len(times) != len(closes) or not closes:
            return

        mapping: dict[str, str] = {}
        for ts, close in zip(times, closes, strict=True):
            if close is None or close <= 0:
                continue
            day = datetime.fromtimestamp(float(ts), tz=UTC).date().isoformat()
            mapping[day] = str(close)

        if mapping:
            await redis.hset(f"{_PRICE_HISTORY_PREFIX}{symbol}", mapping=mapping)
            logger.info("Seeded %d days of history for %s", len(mapping), symbol)
    except Exception as exc:  # noqa: BLE001 — bootstrap is best-effort
        logger.warning("Finnhub candle bootstrap failed for %s: %s", symbol, exc)


# ── Risk computation ──────────────────────────────────────────────────────────


def _holdings_to_weights(
    holdings: list[Holding],
) -> dict[str, tuple[float, float]]:
    """Map holdings to the (quantity, average_price) shape Phase 8 expects."""
    result: dict[str, tuple[float, float]] = {}
    for h in holdings:
        result[h.symbol] = (float(h.quantity), float(h.average_price))
    return result


def _assemble_price_frame(history: dict[str, dict[str, str]]) -> pd.DataFrame:
    """Turn {symbol: {date: close}} into a sorted date-indexed price DataFrame.

    A symbol with no history contributes an all-NaN column; downstream
    covariance estimation drops the row and raises InsufficientDataError, which
    is exactly the conservative behaviour the spec's F5 edge case requires.
    """
    frame: dict[str, pd.Series] = {}
    for symbol, closes in history.items():
        frame[symbol] = pd.Series({d: float(v) for d, v in closes.items()})
    prices = pd.DataFrame(frame) if frame else pd.DataFrame()
    if not prices.empty:
        prices = prices.sort_index()
    return prices


def compute_risk_from_history(
    history: dict[str, dict[str, str]],
    holdings: list[Holding],
) -> tuple[str, RiskEstimate | None, str | None]:
    """Run the Phase 8 quant engine over assembled price history.

    Returns ``(data_status, estimate, estimator)`` where data_status is one of
    ``ready`` / ``insufficient_data``.  Never raises for data-shape problems —
    anything insufficient is mapped to ``insufficient_data``.
    """
    prices = _assemble_price_frame(history)
    if len(prices) < 2:
        return "insufficient_data", None, None

    weights_map = _holdings_to_weights(holdings)
    try:
        returns: ReturnSeries = compute_returns(prices, kind="log")
        weights = compute_weights(weights_map)
        portfolio_returns = compute_portfolio_returns(returns, weights)
        cov_result = estimate_covariance(returns.values)
    except (ValueError, InsufficientDataError):
        return "insufficient_data", None, None

    weight_vec = np.asarray([weights[sym] for sym in cov_result.symbols], dtype=float)
    estimate = compute_risk_estimate(
        portfolio_returns.values,
        weight_vec,
        cov_result.matrix,
        cov_result.symbols,
    )

    if estimate.insufficient_data:
        return "insufficient_data", None, []
        
    from quant.risk_metrics import cov_to_corr, detect_correlation_clusters
    corr = cov_to_corr(cov_result.matrix)
    clusters = detect_correlation_clusters(corr, cov_result.symbols)

    return "ready", estimate, clusters


def _metrics_payload(estimate: RiskEstimate) -> dict[str, float | int | None]:
    """Convert a RiskEstimate into a JSON-serialisable metrics dict."""
    return {
        "var_95": estimate.var_95,
        "cvar_95": estimate.cvar_95,
        "volatility": estimate.volatility,
        "sharpe": estimate.sharpe,
        "max_drawdown": estimate.max_drawdown,
        "n_obs": estimate.n_obs,
    }


def _contributions_payload(estimate: RiskEstimate) -> list[dict[str, float | str]]:
    return [
        {
            "symbol": rc.symbol,
            "weight": rc.weight,
            "mcr": rc.mcr,
            "rc": rc.rc,
            "rc_pct": rc.rc_pct,
        }
        for rc in estimate.risk_contributions
    ]


async def recompute_portfolio(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: str,
    finnhub_api_key: str,
    seeded: set[str],
) -> None:
    """Recompute one portfolio's risk and push the merged state to Redis.

    The published ``risk_update`` payload includes the fast-path values read
    back from the shared ``risk_state:{pid}`` hash so WS clients always get a
    complete picture.
    """
    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == uuid.UUID(portfolio_id))
    )
    holdings = list(result.scalars().all())
    if not holdings:
        return

    # Seed any not-yet-seen symbols and load the daily-close buffers.
    history: dict[str, dict[str, str]] = {}
    for h in holdings:
        await seed_price_history(redis, h.symbol, finnhub_api_key, seeded)
        closes = await redis.hgetall(f"{_PRICE_HISTORY_PREFIX}{h.symbol}")
        history[h.symbol] = dict(closes)

    data_status, estimate, clusters = compute_risk_from_history(history, holdings)
    now_unix = time.time()

    risk_field = json.dumps(
        {
            "data_status": data_status,
            "metrics": _metrics_payload(estimate) if estimate else None,
            "risk_contributions": _contributions_payload(estimate) if estimate else [],
            "correlation_flags": clusters if clusters else [],
            "risk_updated_at": now_unix,
        }
    )
    await redis.hset(f"{_RISK_STATE_PREFIX}{portfolio_id}", "risk", risk_field)

    current = await redis.hgetall(f"{_RISK_STATE_PREFIX}{portfolio_id}")
    await redis.publish(
        f"{_RISK_UPDATES_PREFIX}{portfolio_id}",
        json.dumps(
            {
                "type": "risk_update",
                "portfolio_id": portfolio_id,
                "data_status": data_status,
                "metrics": _metrics_payload(estimate) if estimate else None,
                "risk_contributions": (
                    _contributions_payload(estimate) if estimate else []
                ),
                "correlation_flags": clusters if clusters else [],
                "risk_updated_at": now_unix,
                "portfolio_value": current.get("portfolio_value"),
                "daily_pnl": current.get("daily_pnl"),
                "timestamp": current.get("timestamp"),
            }
        ),
    )

    logger.info("Recomputed risk for portfolio %s -> %s", portfolio_id, data_status)

    # ── Phase 14: alert state machine ────────────────────────────────────────
    if estimate is not None:
        try:
            await _check_alert_state(db, redis, portfolio_id, estimate.cvar_95)
        except Exception:
            logger.exception("Alert state check failed for portfolio %s (isolated)", portfolio_id)


# ── Alert state machine integration ───────────────────────────────────────────

_ALERT_STATE_KEY = "alert_state"   # field inside risk_state:{pid} hash
_LAST_ALERT_KEY = "last_alert_at"  # ISO timestamp of last alert
_BUDGET_CACHE_KEY = "alert_budget"  # cached budget JSON in risk_state hash
_BUDGET_CACHE_TTL = 60              # seconds before re-fetching budget from DB
_BUDGET_CACHE_FETCHED_KEY = "alert_budget_fetched_at"


async def _check_alert_state(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: str,
    cvar_95: float,
) -> None:
    """Load risk budget, compute utilization, run state machine, fire alert if needed.

    Budget is cached in the risk_state Redis hash for 60 s to avoid a DB
    round-trip on every tick.
    """
    state_key = f"{_RISK_STATE_PREFIX}{portfolio_id}"

    # Load cached budget (refresh from DB if stale)
    budget_json = await redis.hget(state_key, _BUDGET_CACHE_KEY)
    fetched_at_str = await redis.hget(state_key, _BUDGET_CACHE_FETCHED_KEY)
    now_ts = time.time()
    cache_stale = (
        budget_json is None
        or fetched_at_str is None
        or (now_ts - float(fetched_at_str)) > _BUDGET_CACHE_TTL
    )

    if cache_stale:
        result = await db.execute(
            select(RiskBudget).where(RiskBudget.portfolio_id == uuid.UUID(portfolio_id))
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            # No budget configured — nothing to alert on
            return
        budget_data = {
            "max_cvar": float(budget.max_cvar),
            "watch": float(budget.watch_threshold),
            "high": float(budget.high_threshold),
            "breach": float(budget.breach_threshold),
        }
        await redis.hset(state_key, _BUDGET_CACHE_KEY, json.dumps(budget_data))
        await redis.hset(state_key, _BUDGET_CACHE_FETCHED_KEY, str(now_ts))
    else:
        budget_data = json.loads(budget_json)  # type: ignore[arg-type]

    # Compute utilization and new state
    util = compute_utilization(cvar_95, budget_data["max_cvar"])

    prev_state_str = await redis.hget(state_key, _ALERT_STATE_KEY)
    prev_state: AlertState | None = prev_state_str  # type: ignore[assignment]

    new_state = compute_state(
        util,
        watch_threshold=budget_data["watch"],
        high_threshold=budget_data["high"],
        breach_threshold=budget_data["breach"],
        prev_state=prev_state,
    )

    last_alert_str = await redis.hget(state_key, _LAST_ALERT_KEY)
    last_alert_at = (
        datetime.fromisoformat(last_alert_str) if last_alert_str else None
    )

    if not should_fire_alert(prev_state, new_state, last_alert_at):
        # Update stored state even if no alert fires (state may have changed silently)
        await redis.hset(state_key, _ALERT_STATE_KEY, new_state)
        return

    # Write alert row (linked to the most recent snapshot for this portfolio)
    from sqlalchemy import select as sa_select
    from app.risk.models import RiskSnapshot
    snap_result = await db.execute(
        sa_select(RiskSnapshot)
        .where(RiskSnapshot.portfolio_id == uuid.UUID(portfolio_id))
        .order_by(RiskSnapshot.captured_at.desc())
        .limit(1)
    )
    latest_snapshot = snap_result.scalar_one_or_none()

    alert = Alert(
        portfolio_id=uuid.UUID(portfolio_id),
        risk_snapshot_id=(
            latest_snapshot.id
            if latest_snapshot is not None
            else uuid.UUID(int=0)  # sentinel — no snapshot yet
        ),
        from_state=prev_state or "SAFE",
        to_state=new_state,
        fired_at=datetime.now(UTC),
    )
    db.add(alert)
    await db.commit()

    # Publish WS alert message
    await redis.publish(
        f"{_RISK_UPDATES_PREFIX}{portfolio_id}",
        json.dumps({
            "type": "alert",
            "portfolio_id": portfolio_id,
            "from_state": prev_state or "SAFE",
            "to_state": new_state,
            "utilization": round(util, 4),
            "cvar": round(cvar_95, 2),
            "fired_at": alert.fired_at.isoformat(),
        }),
    )

    # Update Redis state
    await redis.hset(state_key, _ALERT_STATE_KEY, new_state)
    await redis.hset(state_key, _LAST_ALERT_KEY, alert.fired_at.isoformat())

    logger.info(
        "Alert fired for portfolio %s: %s -> %s (util=%.2f)",
        portfolio_id, prev_state, new_state, util,
    )


# ── Snapshot persistence ──────────────────────────────────────────────────────


async def persist_snapshot(
    db: AsyncSession,
    portfolio_id: str,
    estimate: RiskEstimate,
    captured_at: datetime,
    alert_state: str = "SAFE",
    correlation_flags: list[list[str]] | None = None,
) -> None:
    """Persist an append-only ``risk_snapshots`` audit row (F5: ~every 5 min).

    alert_state is the current SAFE/WATCH/HIGH/BREACH state from the Phase 14
    state machine, written into the risk_state column for the audit trail.
    risk_contribution and correlation_flags are populated in Phase 15.
    """
    snapshot = RiskSnapshot(
        portfolio_id=uuid.UUID(portfolio_id),
        captured_at=captured_at,
        var_95=Decimal(str(estimate.var_95)).quantize(Decimal("0.01")),
        cvar_95=Decimal(str(estimate.cvar_95)).quantize(Decimal("0.01")),
        volatility=Decimal(str(estimate.volatility)).quantize(Decimal("0.000001")),
        max_drawdown=Decimal(str(estimate.max_drawdown)).quantize(Decimal("0.000001")),
        sharpe=(
            Decimal(str(estimate.sharpe)).quantize(Decimal("0.0001"))
            if estimate.sharpe is not None
            else None
        ),
        risk_state=alert_state,          # Phase 14: real state from state machine
        risk_contribution={rc.symbol: rc.rc_pct for rc in estimate.risk_contributions} if estimate.risk_contributions else {},
        correlation_flags=correlation_flags or [],
    )
    db.add(snapshot)
    await db.commit()


# ── Main loop ────────────────────────────────────────────────────────────────


def _load_settings() -> tuple[str, str, str]:
    """Return (redis_url, db_url, finnhub_api_key) from the environment."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL missing.")
        sys.exit(1)
    finnhub_api_key = os.environ.get("FINNHUB_API_KEY", "")
    return redis_url, db_url, finnhub_api_key


async def _ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        logger.info("Created consumer group %s", GROUP_NAME)
    except Exception as exc:  # noqa: BLE001 — BUSYGROUP is expected on restart
        if "BUSYGROUP" not in str(exc):
            logger.error("Error creating consumer group: %s", exc)


async def _flush_portfolio(
    session_factory: async_sessionmaker[AsyncSession],
    redis: Redis,
    portfolio_id: str,
    finnhub_api_key: str,
    seeded: set[str],
    last_snapshot_at: dict[str, float],
    now: float,
) -> None:
    """Recompute a single portfolio, isolated from all others (F5 Errors rule).

    A raised exception here must never stop the worker loop — callers (and the
    loop itself) treat this as per-portfolio unit of work.
    """
    async with session_factory() as db:
        try:
            await recompute_portfolio(db, redis, portfolio_id, finnhub_api_key, seeded)
        except Exception:
            logger.exception("Portfolio %s recompute failed (isolated)", portfolio_id)
            return

        # Coarse-interval snapshot persistence for the DB audit trail.
        if now - last_snapshot_at.get(portfolio_id, -1.0) >= SNAPSHOT_INTERVAL_SECONDS:
            try:
                risk_json = await redis.hget(
                    f"{_RISK_STATE_PREFIX}{portfolio_id}", "risk"
                )
                if risk_json:
                    risk_data: dict[str, Any] = json.loads(risk_json)
                    estimate_data = risk_data.get("metrics")
                    if risk_data.get("data_status") == "ready" and estimate_data:
                        estimate = RiskEstimate(
                            volatility=float(estimate_data["volatility"]),
                            var_95=float(estimate_data["var_95"]),
                            cvar_95=float(estimate_data["cvar_95"]),
                            sharpe=(
                                float(estimate_data["sharpe"])
                                if estimate_data.get("sharpe") is not None
                                else None
                            ),
                            max_drawdown=float(estimate_data["max_drawdown"]),
                        )
                        # Read current alert state from Redis for snapshot audit
                        alert_state = await redis.hget(
                            f"{_RISK_STATE_PREFIX}{portfolio_id}", _ALERT_STATE_KEY
                        ) or "SAFE"
                        flags = risk_data.get("correlation_flags") or []
                        await persist_snapshot(
                            db, portfolio_id, estimate, datetime.now(UTC),
                            alert_state=alert_state,
                            correlation_flags=flags,
                        )
                        last_snapshot_at[portfolio_id] = now
            except Exception:
                logger.exception(
                    "Snapshot persistence failed for portfolio %s", portfolio_id
                )


async def run_slow_path() -> None:
    redis_url, db_url, finnhub_api_key = _load_settings()
    redis = Redis.from_url(redis_url, decode_responses=True)
    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await _ensure_group(redis)

    batcher = WindowBatcher()
    seeded: set[str] = set()
    last_snapshot_at: dict[str, float] = {}

    logger.info("Starting slow path consumer loop...")

    while True:
        now = time.monotonic()
        try:
            messages = await redis.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=BATCH_SIZE,
                block=BLOCK_MS,
            )

            for _stream, entries in messages:
                for msg_id, data in entries:
                    symbol = data.get("symbol")
                    price = data.get("price")
                    timestamp_str = data.get("timestamp")
                    if not symbol or not price or not timestamp_str:
                        await redis.xack(STREAM_NAME, GROUP_NAME, msg_id)
                        continue

                    await seed_price_history(redis, symbol, finnhub_api_key, seeded)
                    await record_tick(redis, symbol, price, float(timestamp_str))

                    affected = await redis.smembers(f"{_REVERSE_INDEX_PREFIX}{symbol}")
                    batcher.add(set(affected), now)

                    await redis.xack(STREAM_NAME, GROUP_NAME, msg_id)

            if batcher.should_flush(now):
                for portfolio_id in batcher.drain():
                    await _flush_portfolio(
                        session_factory,
                        redis,
                        portfolio_id,
                        finnhub_api_key,
                        seeded,
                        last_snapshot_at,
                        now,
                    )

        except Exception as exc:
            logger.error("Error in slow path worker loop: %s", exc, exc_info=True)
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_slow_path())
    except KeyboardInterrupt:
        logger.info("Slow path worker shut down.")
