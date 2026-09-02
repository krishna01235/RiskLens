"""
tests/integration/test_simulation_lifecycle.py

Integration tests for Phase 12: simulation lifecycle (create -> run -> complete/fail),
rate limiting, concurrency limit, and ownership enforcement.

These tests do NOT require a live Redis or arq worker -- the job function is called
directly (bypassing the queue) to test the full lifecycle end-to-end.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import insert

from app.portfolios.models import Portfolio
from app.simulations.models import Simulation
from app.simulations import service as sim_service
from app.simulations.schemas import SimulationCreateRequest, SimulationResultPayload


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_portfolio(db_session, user_id: uuid.UUID) -> Portfolio:
    """Insert a minimal portfolio row for the test user."""
    from app.portfolios.models import Portfolio
    p = Portfolio(
        user_id=user_id,
        name="Test Portfolio",
        currency="USD",
        source="manual",
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# 1. Happy-path: POST /simulations -> 202 with status=pending
# ---------------------------------------------------------------------------


async def test_create_simulation_returns_pending(async_client, db_session, auth_headers, test_user):
    """POST /simulations should return 202 with status=pending."""
    portfolio = await _create_portfolio(db_session, test_user.id)

    with patch("app.simulations.router.create_pool") as mock_pool_factory:
        mock_pool = AsyncMock()
        mock_pool_factory.return_value = mock_pool

        resp = await async_client.post(
            "/simulations",
            json={
                "portfolio_id": str(portfolio.id),
                "horizon_days": 30,
                "num_paths": 10000,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["portfolio_id"] == str(portfolio.id)
    assert data["horizon_days"] == 30
    assert data["num_paths"] == 10000
    assert data["results"] is None


# ---------------------------------------------------------------------------
# 2. GET /simulations/{id} -> ownership-scoped fetch
# ---------------------------------------------------------------------------


async def test_get_simulation_owned(async_client, db_session, auth_headers, test_user):
    """GET /simulations/{id} returns the simulation for its owner."""
    portfolio = await _create_portfolio(db_session, test_user.id)
    sim = Simulation(
        portfolio_id=portfolio.id,
        horizon_days=7,
        num_paths=10000,
        status="pending",
    )
    db_session.add(sim)
    await db_session.commit()

    resp = await async_client.get(f"/simulations/{sim.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(sim.id)


async def test_get_simulation_another_user_returns_404(async_client, db_session, auth_headers):
    """Simulation belonging to another user must return 404."""
    other_user_id = uuid.uuid4()
    portfolio = Portfolio(
        user_id=other_user_id,
        name="Other Portfolio",
        currency="USD",
        source="manual",
    )
    db_session.add(portfolio)
    await db_session.commit()

    sim = Simulation(
        portfolio_id=portfolio.id,
        horizon_days=7,
        num_paths=10000,
        status="pending",
    )
    db_session.add(sim)
    await db_session.commit()

    resp = await async_client.get(f"/simulations/{sim.id}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. Failure path: job exception -> status=failed, never stuck pending
# ---------------------------------------------------------------------------


async def test_job_failure_marks_failed(db_session, test_user):
    """If the job raises an exception, status must transition to failed."""
    portfolio = await _create_portfolio(db_session, test_user.id)
    sim = Simulation(
        portfolio_id=portfolio.id,
        horizon_days=30,
        num_paths=10000,
        status="pending",
    )
    db_session.add(sim)
    await db_session.commit()
    await db_session.refresh(sim)

    # Import the actual job function and call it directly (no arq queue)
    from workers.job_worker import run_monte_carlo_job

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.publish = AsyncMock()

    # Patch _build_params to raise a RuntimeError mid-job
    with patch("workers.job_worker._build_params", side_effect=RuntimeError("Simulated failure")):
        ctx = {"redis": mock_redis}
        await run_monte_carlo_job(ctx, str(sim.id))

    await db_session.refresh(sim)
    assert sim.status == "failed", f"Expected failed, got {sim.status}"
    assert sim.error_message is not None
    assert "Simulated failure" in sim.error_message
    assert sim.completed_at is not None


# ---------------------------------------------------------------------------
# 4. Rate limit: 11th simulation in an hour -> 429
# ---------------------------------------------------------------------------


async def test_rate_limit_exceeded(async_client, db_session, auth_headers, test_user):
    """The 11th simulation request within an hour must return 429."""
    portfolio = await _create_portfolio(db_session, test_user.id)

    # Seed 10 simulations in the last hour for this user
    for _ in range(10):
        sim = Simulation(
            portfolio_id=portfolio.id,
            horizon_days=1,
            num_paths=10000,
            status="complete",
            created_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        db_session.add(sim)
    await db_session.commit()

    with patch("app.simulations.router.create_pool") as mock_pool_factory:
        mock_pool = AsyncMock()
        mock_pool_factory.return_value = mock_pool

        resp = await async_client.post(
            "/simulations",
            json={
                "portfolio_id": str(portfolio.id),
                "horizon_days": 1,
                "num_paths": 10000,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 429, resp.text


# ---------------------------------------------------------------------------
# 5. Concurrency limit: second concurrent simulation -> 409
# ---------------------------------------------------------------------------


async def test_concurrent_simulation_conflict(async_client, db_session, auth_headers, test_user):
    """A second in-progress simulation for the same portfolio must return 409."""
    portfolio = await _create_portfolio(db_session, test_user.id)

    # Existing running simulation
    sim = Simulation(
        portfolio_id=portfolio.id,
        horizon_days=30,
        num_paths=10000,
        status="running",
    )
    db_session.add(sim)
    await db_session.commit()

    with patch("app.simulations.router.create_pool") as mock_pool_factory:
        mock_pool = AsyncMock()
        mock_pool_factory.return_value = mock_pool

        resp = await async_client.post(
            "/simulations",
            json={
                "portfolio_id": str(portfolio.id),
                "horizon_days": 7,
                "num_paths": 10000,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# 6. service.mark_complete -> status=complete with results
# ---------------------------------------------------------------------------


async def test_mark_complete_stores_results(db_session, test_user):
    """mark_complete must persist results JSON and flip status."""
    portfolio = await _create_portfolio(db_session, test_user.id)
    sim = Simulation(
        portfolio_id=portfolio.id,
        horizon_days=30,
        num_paths=10000,
        status="running",
    )
    db_session.add(sim)
    await db_session.commit()

    results = SimulationResultPayload(
        prob_profit=0.60,
        prob_loss=0.38,
        expected_pnl=250.0,
        pnl_p5=-500.0,
        pnl_p50=230.0,
        pnl_p95=1100.0,
        num_paths=10000,
    )
    await sim_service.mark_complete(db_session, sim.id, results)

    await db_session.refresh(sim)
    assert sim.status == "complete"
    assert sim.results is not None
    assert abs(sim.results["prob_profit"] - 0.60) < 1e-9
    assert sim.completed_at is not None
