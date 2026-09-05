"""Unit tests for workers/slow_path_worker.py — batching, buffers, risk compute."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import numpy as np

import app.ai.models  # noqa: F401  # resolve full mapper graph before use
import app.alerts.models  # noqa: F401
import app.auth.models  # noqa: F401
import app.portfolios.models  # noqa: F401
import app.replays.models  # noqa: F401
import app.risk.models  # noqa: F401
import app.simulations.models  # noqa: F401
from app.portfolios.models import Holding
from quant.risk_metrics import RiskEstimate
from workers.slow_path_worker import (
    WindowBatcher,
    _contributions_payload,
    _metrics_payload,
    compute_risk_from_history,
    record_tick,
)

# ── WindowBatcher ─────────────────────────────────────────────────────────────


class TestWindowBatcher:
    def test_count_trigger_flushes(self) -> None:
        batcher = WindowBatcher(max_ticks=3, max_seconds=10)
        batcher.add({"A"}, 0.0)
        batcher.add({"A", "B"}, 0.1)
        assert batcher.should_flush(0.1) is False
        batcher.add({"C"}, 0.2)
        assert batcher.should_flush(0.2) is True
        assert batcher.drain() == {"A", "B", "C"}

    def test_time_trigger_flushes(self) -> None:
        batcher = WindowBatcher(max_ticks=100, max_seconds=2.0)
        batcher.add({"A"}, 0.0)
        assert batcher.should_flush(1.9) is False
        assert batcher.should_flush(2.0) is True

    def test_empty_window_is_skipped(self) -> None:
        batcher = WindowBatcher()
        assert batcher.should_flush(100.0) is False
        assert batcher.drain() == set()

    def test_drain_resets_window(self) -> None:
        batcher = WindowBatcher(max_ticks=1)
        batcher.add({"A"}, 0.0)
        batcher.drain()
        assert batcher.should_flush(1.0) is False
        assert batcher._tick_count == 0

    def test_add_without_portfolios_is_noop(self) -> None:
        batcher = WindowBatcher(max_ticks=1, max_seconds=0.1)
        batcher.add(set(), 0.0)
        batcher.add(set(), 0.2)
        assert batcher.should_flush(0.2) is False
        assert batcher.drain() == set()


# ── record_tick ───────────────────────────────────────────────────────────────


class TestRecordTick:
    async def test_upserts_today_close(self) -> None:
        redis = AsyncMock()
        redis.hkeys = AsyncMock(return_value=["2026-08-01"])
        await record_tick(redis, "AAPL", "150.0", 1710000000.0)
        redis.hset.assert_awaited_once()
        redis.hdel.assert_not_awaited()

    async def test_prunes_oldest_when_over_cap(self) -> None:
        redis = AsyncMock()
        days = [
            (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i)).date().isoformat()
            for i in range(260)
        ]
        redis.hkeys = AsyncMock(return_value=days)
        await record_tick(redis, "AAPL", "150.0", 1710000000.0)
        redis.hdel.assert_awaited_once()
        removed = list(redis.hdel.await_args.args[1:])  # type: ignore[union-attr]
        assert len(removed) == 10  # 260 fields returned + 1 inserted -> cap 250
        assert removed == days[:10]


def _make_history(
    symbols: list[str], n_days: int = 60, seed: int = 0
) -> dict[str, dict[str, str]]:
    """Synthetic noisy random-walk daily close history for *symbols*."""
    rng = np.random.default_rng(seed)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    days = [(base + timedelta(days=i)).date().isoformat() for i in range(n_days)]
    history: dict[str, dict[str, str]] = {}
    for sym in symbols:
        price = 100.0
        history[sym] = {}
        for day in days:
            price *= 1.0 + rng.normal(0.0005, 0.02)
            history[sym][day] = str(price)
    return history


def _holdings(*symbols: str) -> list[Holding]:
    return [
        Holding(symbol=sym, quantity=Decimal("10"), average_price=Decimal("100"))
        for sym in symbols
    ]


class TestComputeRiskFromHistory:
    def test_ready_path_produces_metrics(self) -> None:
        history = _make_history(["AAPL", "MSFT"], n_days=60)
        status, estimate, clusters = compute_risk_from_history(
            history, _holdings("AAPL", "MSFT")
        )
        assert status == "ready"
        assert isinstance(clusters, list)
        assert estimate is not None
        assert estimate.var_95 > 0
        assert estimate.cvar_95 >= estimate.var_95
        assert estimate.n_obs >= 30

    def test_no_history_returns_insufficient(self) -> None:
        status, estimate, clusters = compute_risk_from_history({}, _holdings("AAPL"))
        assert status == "insufficient_data"
        assert estimate is None
        assert clusters is None

    def test_single_day_returns_insufficient(self) -> None:
        history = _make_history(["AAPL"], n_days=1)
        status, _est, _estimator = compute_risk_from_history(history, _holdings("AAPL"))
        assert status == "insufficient_data"

    def test_symbol_without_history_is_insufficient(self) -> None:
        history = _make_history(["AAPL"], n_days=60)
        status, _est, _estimator = compute_risk_from_history(
            history, _holdings("AAPL", "MSFT")
        )
        assert status == "insufficient_data"


# ── Payload helpers ───────────────────────────────────────────────────────────


class TestPayloadHelpers:
    def test_metrics_payload_full(self) -> None:
        estimate = RiskEstimate(
            volatility=0.25,
            var_95=100.0,
            cvar_95=150.0,
            sharpe=1.5,
            max_drawdown=0.2,
        )
        payload = _metrics_payload(estimate)
        assert payload["var_95"] == 100.0
        assert payload["sharpe"] == 1.5
        assert payload["max_drawdown"] == 0.2

    def test_contributions_payload_empty(self) -> None:
        estimate = RiskEstimate(
            volatility=0.25,
            var_95=100.0,
            cvar_95=150.0,
            sharpe=None,
            max_drawdown=0.2,
        )
        assert _contributions_payload(estimate) == []
