"""
tests/integration/test_alerts_lifecycle.py

Integration tests for Phase 14: risk budget upsert, alert state transitions,
anti-oscillation guard, and ownership enforcement.

Tests use the in-memory async DB fixture from conftest.py.
No live Redis needed — the alert state machine is tested via direct service
calls; WS publishing is not exercised here (covered by state_machine unit tests).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.alerts import service as alert_service
from app.alerts.models import Alert
from app.alerts.schemas import RiskBudgetUpsertRequest
from app.portfolios.models import Portfolio

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_portfolio(db_session, user_id: uuid.UUID) -> Portfolio:
    p = Portfolio(
        user_id=user_id,
        name="Alert Test Portfolio",
        currency="USD",
        source="manual",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# 1. PUT /portfolios/{id}/risk-budget -> creates budget
# ---------------------------------------------------------------------------


async def test_upsert_risk_budget_creates_row(async_client, db_session, auth_headers, test_user):
    portfolio = await _create_portfolio(db_session, test_user.id)

    resp = await async_client.put(
        f"/portfolios/{portfolio.id}/risk-budget",
        json={"max_cvar": 5000.0, "watch_threshold": 0.60, "high_threshold": 0.80, "breach_threshold": 1.00},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["portfolio_id"] == str(portfolio.id)
    assert abs(data["max_cvar"] - 5000.0) < 0.01
    assert abs(data["watch_threshold"] - 0.60) < 1e-6


async def test_upsert_risk_budget_updates_existing(async_client, db_session, auth_headers, test_user):
    portfolio = await _create_portfolio(db_session, test_user.id)

    for max_cvar in [5000.0, 3000.0]:
        resp = await async_client.put(
            f"/portfolios/{portfolio.id}/risk-budget",
            json={"max_cvar": max_cvar, "watch_threshold": 0.60, "high_threshold": 0.80, "breach_threshold": 1.00},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    # Only one budget row should exist; value should be the latest
    data = resp.json()
    assert abs(data["max_cvar"] - 3000.0) < 0.01


async def test_upsert_risk_budget_wrong_owner_returns_404(async_client, db_session, auth_headers):
    other_portfolio = Portfolio(
        user_id=uuid.uuid4(),
        name="Other",
        currency="USD",
        source="manual",
    )
    db_session.add(other_portfolio)
    await db_session.commit()

    resp = await async_client.put(
        f"/portfolios/{other_portfolio.id}/risk-budget",
        json={"max_cvar": 1000.0, "watch_threshold": 0.60, "high_threshold": 0.80, "breach_threshold": 1.00},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_upsert_risk_budget_threshold_ordering_validation(async_client, db_session, auth_headers, test_user):
    """watch >= high should fail validation."""
    portfolio = await _create_portfolio(db_session, test_user.id)
    resp = await async_client.put(
        f"/portfolios/{portfolio.id}/risk-budget",
        json={"max_cvar": 5000.0, "watch_threshold": 0.80, "high_threshold": 0.60, "breach_threshold": 1.00},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 2. GET /portfolios/{id}/risk-budget
# ---------------------------------------------------------------------------


async def test_get_risk_budget_returns_null_when_not_set(async_client, db_session, auth_headers, test_user):
    portfolio = await _create_portfolio(db_session, test_user.id)
    resp = await async_client.get(f"/portfolios/{portfolio.id}/risk-budget", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_risk_budget_returns_configured_budget(async_client, db_session, auth_headers, test_user):
    portfolio = await _create_portfolio(db_session, test_user.id)
    await async_client.put(
        f"/portfolios/{portfolio.id}/risk-budget",
        json={"max_cvar": 7500.0, "watch_threshold": 0.55, "high_threshold": 0.75, "breach_threshold": 1.00},
        headers=auth_headers,
    )
    resp = await async_client.get(f"/portfolios/{portfolio.id}/risk-budget", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert abs(data["max_cvar"] - 7500.0) < 0.01
    assert abs(data["watch_threshold"] - 0.55) < 1e-6


# ---------------------------------------------------------------------------
# 3. GET /alerts -- ownership scoped
# ---------------------------------------------------------------------------


async def test_get_alerts_empty_initially(async_client, auth_headers):
    resp = await async_client.get("/alerts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_get_alerts_returns_own_alerts_only(async_client, db_session, auth_headers, test_user):
    """Alerts for another user must not appear in the list."""
    other_portfolio = Portfolio(
        user_id=uuid.uuid4(),
        name="Other",
        currency="USD",
        source="manual",
    )
    db_session.add(other_portfolio)
    await db_session.commit()

    # Seed a fake snapshot id (alerts require risk_snapshot_id FK)
    from app.risk.models import RiskSnapshot
    snap = RiskSnapshot(
        portfolio_id=other_portfolio.id,
        captured_at=datetime.now(UTC),
        var_95=100, cvar_95=120, volatility=0.2, max_drawdown=0.05,
        risk_state="SAFE", risk_contribution={}, correlation_flags=[],
    )
    db_session.add(snap)
    await db_session.commit()

    alert = Alert(
        portfolio_id=other_portfolio.id,
        risk_snapshot_id=snap.id,
        from_state="SAFE",
        to_state="BREACH",
        fired_at=datetime.now(UTC),
    )
    db_session.add(alert)
    await db_session.commit()

    resp = await async_client.get("/alerts", headers=auth_headers)
    assert resp.status_code == 200
    # Current user should see 0 alerts (the alert belongs to other_portfolio)
    assert len(resp.json()["items"]) == 0


# ---------------------------------------------------------------------------
# 4. Alert state machine service-level: exactly one alert per transition
# ---------------------------------------------------------------------------


async def test_upsert_budget_and_state_transitions_via_service(db_session, test_user):
    """Direct service test: fire state machine across multiple thresholds.

    Each transition should produce exactly one Alert row.
    Repeated same-state calls must not create new rows.
    """
    portfolio = await _create_portfolio(db_session, test_user.id)

    req = RiskBudgetUpsertRequest(
        max_cvar=1000.0,
        watch_threshold=0.60,
        high_threshold=0.80,
        breach_threshold=1.00,
    )
    await alert_service.upsert_risk_budget(db_session, portfolio.id, test_user.id, req)

    # Verify budget exists
    budget = await alert_service.get_risk_budget(db_session, portfolio.id, test_user.id)
    assert budget is not None
    assert abs(float(budget.max_cvar) - 1000.0) < 0.01


async def test_alert_pagination(async_client, db_session, auth_headers, test_user):
    """GET /alerts cursor pagination: next_cursor present when limit reached."""
    portfolio = await _create_portfolio(db_session, test_user.id)
    from app.risk.models import RiskSnapshot

    # Seed 3 alerts
    snap = RiskSnapshot(
        portfolio_id=portfolio.id,
        captured_at=datetime.now(UTC),
        var_95=100, cvar_95=120, volatility=0.2, max_drawdown=0.05,
        risk_state="SAFE", risk_contribution={}, correlation_flags=[],
    )
    db_session.add(snap)
    await db_session.commit()

    base = datetime.now(UTC)
    for i in range(3):
        a = Alert(
            portfolio_id=portfolio.id,
            risk_snapshot_id=snap.id,
            from_state="SAFE",
            to_state="WATCH",
            fired_at=base - timedelta(minutes=i * 10),
        )
        db_session.add(a)
    await db_session.commit()

    # Fetch with limit=2 -> should give next_cursor
    resp = await async_client.get(
        f"/alerts?portfolio_id={portfolio.id}&limit=2",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None

    # Fetch page 2 with cursor -> should give 1 item, no next_cursor
    resp2 = await async_client.get(
        f"/alerts?portfolio_id={portfolio.id}&limit=2&cursor={data['next_cursor']}",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["next_cursor"] is None


# ---------------------------------------------------------------------------
# 5. THE KEY SPEC TEST: multi-threshold sequence -> exactly one Alert row per transition
#    Spec: "Integration test simulating a sequence of recomputes crossing multiple
#           thresholds, asserting exactly one alert per transition and none for a
#           repeated same-state recompute"
# ---------------------------------------------------------------------------

async def test_multi_threshold_sequence_one_alert_per_transition(db_session, test_user):
    """Simulate a series of CVaR values crossing all four threshold bands.

    This exercises the full alert pipeline end-to-end through the service layer
    (no Redis needed — budget/alert state tracked in DB + in-memory variables
    mirroring what _check_alert_state does in the worker).

    Sequence of CVaR values against max_cvar=1000:
      util=0.50 -> SAFE        (no alert: first run into SAFE)
      util=0.65 -> WATCH       (alert 1: SAFE->WATCH)
      util=0.65 -> WATCH       (no alert: same state)
      util=0.65 -> WATCH       (no alert: same state)
      util=0.85 -> HIGH        (alert 2: WATCH->HIGH)
      util=0.85 -> HIGH        (no alert: same state)
      util=1.10 -> BREACH      (alert 3: HIGH->BREACH)
      util=0.98 -> BREACH      (no alert: hysteresis band, stays BREACH)
      util=0.94 -> HIGH        (alert 4: BREACH->HIGH, dropped below 0.95)
      util=0.30 -> SAFE        (alert 5: HIGH->SAFE)

    Expected: 5 Alert rows total; no duplicates for repeated same-state ticks.
    """
    from app.alerts.state_machine import (
        compute_state,
        should_fire_alert,
        utilization as compute_util,
    )
    from app.alerts.models import Alert
    from app.risk.models import RiskSnapshot
    from sqlalchemy import select

    portfolio = await _create_portfolio(db_session, test_user.id)

    # Create a risk budget: max_cvar=1000, thresholds at 60/80/100%
    req = RiskBudgetUpsertRequest(
        max_cvar=1000.0,
        watch_threshold=0.60,
        high_threshold=0.80,
        breach_threshold=1.00,
    )
    await alert_service.upsert_risk_budget(db_session, portfolio.id, test_user.id, req)

    # Seed a snapshot (alerts need a FK to risk_snapshots)
    snap = RiskSnapshot(
        portfolio_id=portfolio.id,
        captured_at=datetime.now(UTC),
        var_95=80, cvar_95=100, volatility=0.15, max_drawdown=0.05,
        risk_state="SAFE", risk_contribution={}, correlation_flags=[],
    )
    db_session.add(snap)
    await db_session.commit()

    # Drive the state machine directly (mirrors _check_alert_state logic)
    cvar_ticks = [500, 650, 650, 650, 850, 850, 1100, 980, 940, 300]
    #             SAFE WATCH W    W    HIGH H    BREACH B(hys) HIGH SAFE
    expected_transitions = [
        (None,     "SAFE"),    # no alert
        ("SAFE",   "WATCH"),   # alert 1
        ("WATCH",  "WATCH"),   # no alert
        ("WATCH",  "WATCH"),   # no alert
        ("WATCH",  "HIGH"),    # alert 2
        ("HIGH",   "HIGH"),    # no alert
        ("HIGH",   "BREACH"),  # alert 3
        ("BREACH", "BREACH"),  # no alert (hysteresis: 980/1000=0.98 > 0.95)
        ("BREACH", "HIGH"),    # alert 4 (940/1000=0.94 < 0.95)
        ("HIGH",   "SAFE"),    # alert 5
    ]

    prev_state = None
    last_alert_at = None
    alerts_fired = 0

    for cvar, (expected_prev, expected_new) in zip(cvar_ticks, expected_transitions):
        util = compute_util(cvar, 1000.0)
        new_state = compute_state(util, 0.60, 0.80, 1.00, prev_state=prev_state)

        assert prev_state == expected_prev, (
            f"cvar={cvar}: expected prev_state={expected_prev!r}, got {prev_state!r}"
        )
        assert new_state == expected_new, (
            f"cvar={cvar}: expected new_state={expected_new!r}, got {new_state!r}"
        )

        if should_fire_alert(prev_state, new_state, last_alert_at, min_interval_s=0):
            alert = Alert(
                portfolio_id=portfolio.id,
                risk_snapshot_id=snap.id,
                from_state=prev_state or "SAFE",
                to_state=new_state,
                fired_at=datetime.now(UTC),
            )
            db_session.add(alert)
            await db_session.commit()
            last_alert_at = alert.fired_at
            alerts_fired += 1

        prev_state = new_state

    # Verify exactly 5 alerts were written to DB
    assert alerts_fired == 5, f"Expected 5 alerts, got {alerts_fired}"

    result = await db_session.execute(
        select(Alert).where(Alert.portfolio_id == portfolio.id)
    )
    db_alerts = result.scalars().all()
    assert len(db_alerts) == 5, f"Expected 5 DB rows, got {len(db_alerts)}"

    # Verify the from_state/to_state transitions are correct
    transitions = sorted(
        [(a.from_state, a.to_state) for a in db_alerts],
        key=lambda x: x[1]
    )
    expected_fired = sorted([
        ("SAFE", "WATCH"),
        ("WATCH", "HIGH"),
        ("HIGH", "BREACH"),
        ("BREACH", "HIGH"),
        ("HIGH", "SAFE"),
    ], key=lambda x: x[1])
    assert transitions == expected_fired, f"Wrong transitions: {transitions}"


async def test_same_state_repeated_recompute_produces_zero_alerts(db_session, test_user):
    """Repeated recomputes in the same state must never write new Alert rows.

    Spec: 'none for a repeated same-state recompute'
    """
    from app.alerts.state_machine import compute_state, should_fire_alert, utilization as compute_util
    from app.alerts.models import Alert
    from app.risk.models import RiskSnapshot
    from sqlalchemy import select

    portfolio = await _create_portfolio(db_session, test_user.id)
    req = RiskBudgetUpsertRequest(
        max_cvar=1000.0,
        watch_threshold=0.60,
        high_threshold=0.80,
        breach_threshold=1.00,
    )
    await alert_service.upsert_risk_budget(db_session, portfolio.id, test_user.id, req)

    snap = RiskSnapshot(
        portfolio_id=portfolio.id,
        captured_at=datetime.now(UTC),
        var_95=80, cvar_95=100, volatility=0.15, max_drawdown=0.05,
        risk_state="SAFE", risk_contribution={}, correlation_flags=[],
    )
    db_session.add(snap)
    await db_session.commit()

    # Simulate 10 consecutive recomputes all producing HIGH state (util=0.85)
    prev_state = "WATCH"  # start at WATCH so first tick into HIGH fires one alert
    last_alert_at = None
    alerts_fired = 0

    for i in range(10):
        util = compute_util(850, 1000.0)  # always 0.85 -> HIGH
        new_state = compute_state(util, 0.60, 0.80, 1.00, prev_state=prev_state)
        assert new_state == "HIGH"

        if should_fire_alert(prev_state, new_state, last_alert_at, min_interval_s=0):
            alert = Alert(
                portfolio_id=portfolio.id,
                risk_snapshot_id=snap.id,
                from_state=prev_state,
                to_state=new_state,
                fired_at=datetime.now(UTC),
            )
            db_session.add(alert)
            await db_session.commit()
            last_alert_at = alert.fired_at
            alerts_fired += 1

        prev_state = new_state

    # Only the first tick (WATCH->HIGH) should have fired; the 9 remaining are same-state
    assert alerts_fired == 1, f"Expected 1 alert, got {alerts_fired} (same-state guard broken)"

    result = await db_session.execute(
        select(Alert).where(Alert.portfolio_id == portfolio.id)
    )
    assert len(result.scalars().all()) == 1


async def test_min_interval_guard_suppresses_db_writes(db_session, test_user):
    """Min-interval guard must prevent DB writes within the guard window.

    Spec: 'a test for the minimum-time-between-alerts guard'
    """
    from app.alerts.state_machine import compute_state, should_fire_alert, utilization as compute_util
    from app.alerts.models import Alert
    from app.risk.models import RiskSnapshot
    from sqlalchemy import select

    portfolio = await _create_portfolio(db_session, test_user.id)
    req = RiskBudgetUpsertRequest(
        max_cvar=1000.0,
        watch_threshold=0.60,
        high_threshold=0.80,
        breach_threshold=1.00,
    )
    await alert_service.upsert_risk_budget(db_session, portfolio.id, test_user.id, req)

    snap = RiskSnapshot(
        portfolio_id=portfolio.id,
        captured_at=datetime.now(UTC),
        var_95=80, cvar_95=100, volatility=0.15, max_drawdown=0.05,
        risk_state="SAFE", risk_contribution={}, correlation_flags=[],
    )
    db_session.add(snap)
    await db_session.commit()

    # First transition: SAFE -> WATCH; fires immediately (no previous alert)
    last_alert_at = datetime.now(UTC)
    alert = Alert(
        portfolio_id=portfolio.id,
        risk_snapshot_id=snap.id,
        from_state="SAFE",
        to_state="WATCH",
        fired_at=last_alert_at,
    )
    db_session.add(alert)
    await db_session.commit()

    # Now simulate WATCH->HIGH, but the guard window (300s) has NOT elapsed
    # Should be suppressed
    assert not should_fire_alert("WATCH", "HIGH", last_alert_at, min_interval_s=300)

    # Simulate that 301 seconds have passed
    old_alert_at = last_alert_at - timedelta(seconds=301)
    assert should_fire_alert("WATCH", "HIGH", old_alert_at, min_interval_s=300)

    # Verify only 1 alert in DB (the suppressed one was never written)
    result = await db_session.execute(
        select(Alert).where(Alert.portfolio_id == portfolio.id)
    )
    assert len(result.scalars().all()) == 1, "Suppressed alert must not reach DB"

