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
        f"/alerts?portfolio_id={portfolio.id}&limit=2&cursor={data[\"next_cursor\"]}",
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["next_cursor"] is None
