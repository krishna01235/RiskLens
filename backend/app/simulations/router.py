"""simulations/router.py -- POST /simulations, GET /simulations/{id}."""

from __future__ import annotations

import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.simulations import service
from app.simulations.schemas import SimulationCreateRequest, SimulationResponse

simulations_router = APIRouter(prefix="/simulations", tags=["simulations"])
_settings = get_settings()


@simulations_router.post("", response_model=SimulationResponse, status_code=202)
async def create_simulation(
    req: SimulationCreateRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> SimulationResponse:
    """Create a simulation job and enqueue it for async execution.

    Returns 202 Accepted with status=pending immediately.
    Poll GET /simulations/{id} or listen for WS simulation_progress messages.
    """
    sim = await service.create_simulation(db, req, current_user.id)

    # Enqueue the arq job
    try:
        redis_settings = RedisSettings.from_dsn(_settings.redis_url)
        pool = await create_pool(redis_settings)
        await pool.enqueue_job("run_monte_carlo_job", str(sim.id))
        await pool.aclose()
    except Exception:
        # If Redis is unavailable, the row stays pending; the worker will
        # pick it up on reconnect (acceptable for MVP — documented limitation).
        pass

    return SimulationResponse.model_validate(sim)


@simulations_router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> SimulationResponse:
    """Poll or fetch the final result of a simulation (ownership-scoped)."""
    sim = await service.get_simulation(db, simulation_id, current_user.id)
    return SimulationResponse.model_validate(sim)
