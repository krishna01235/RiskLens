"""simulations/service.py -- Business logic for simulation lifecycle.

Ownership and rate-limit enforcement per the ownership-and-security-review skill:
  - Every read/write is scoped to the requesting user_id.
  - Rate limits checked BEFORE any DB write.
  - Status transitions are explicit named functions (never raw string updates).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolios.models import Portfolio
from app.simulations.models import Simulation
from app.simulations.schemas import SimulationCreateRequest, SimulationResultPayload

# Rate-limit constants (spec §11)
_MAX_PER_HOUR = 10
_MAX_CONCURRENT = 1


async def _assert_portfolio_owned(
    db: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Raise 404 if portfolio does not exist or is not owned by user."""
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")


async def _check_rate_limits(
    db: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Raise 429 (hourly) or 409 (concurrent) if limits exceeded."""
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

    # Hourly limit: count simulations created in the last hour for this user
    hourly_count_result = await db.execute(
        select(func.count(Simulation.id))
        .join(Portfolio, Portfolio.id == Simulation.portfolio_id)
        .where(
            Portfolio.user_id == user_id,
            Simulation.created_at >= one_hour_ago,
        )
    )
    hourly_count = hourly_count_result.scalar_one()
    if hourly_count >= _MAX_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {_MAX_PER_HOUR} simulations per hour.",
        )

    # Concurrency limit: count running simulations for this portfolio
    concurrent_result = await db.execute(
        select(func.count(Simulation.id)).where(
            Simulation.portfolio_id == portfolio_id,
            Simulation.status.in_(["pending", "running"]),
        )
    )
    concurrent = concurrent_result.scalar_one()
    if concurrent >= _MAX_CONCURRENT:
        raise HTTPException(
            status_code=409,
            detail="Another simulation is already running for this portfolio.",
        )


async def create_simulation(
    db: AsyncSession,
    req: SimulationCreateRequest,
    user_id: uuid.UUID,
) -> Simulation:
    """Create a simulation row (status=pending) after ownership + rate-limit checks."""
    await _assert_portfolio_owned(db, req.portfolio_id, user_id)
    await _check_rate_limits(db, req.portfolio_id, user_id)

    sim = Simulation(
        portfolio_id=req.portfolio_id,
        horizon_days=req.horizon_days,
        num_paths=req.num_paths,
        status="pending",
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)
    return sim


async def get_simulation(
    db: AsyncSession, simulation_id: uuid.UUID, user_id: uuid.UUID
) -> Simulation:
    """Fetch a simulation by id, scoped to the requesting user."""
    result = await db.execute(
        select(Simulation)
        .join(Portfolio, Portfolio.id == Simulation.portfolio_id)
        .where(
            Simulation.id == simulation_id,
            Portfolio.user_id == user_id,
        )
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return sim


async def mark_running(db: AsyncSession, simulation_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if sim:
        sim.status = "running"
        await db.commit()


async def mark_complete(
    db: AsyncSession,
    simulation_id: uuid.UUID,
    results: SimulationResultPayload,
) -> None:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if sim:
        sim.status = "complete"
        sim.results = results.model_dump()
        sim.completed_at = datetime.now(UTC)
        await db.commit()


async def mark_failed(
    db: AsyncSession, simulation_id: uuid.UUID, error_message: str
) -> None:
    result = await db.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    sim = result.scalar_one_or_none()
    if sim:
        sim.status = "failed"
        sim.error_message = error_message
        sim.completed_at = datetime.now(UTC)
        await db.commit()
