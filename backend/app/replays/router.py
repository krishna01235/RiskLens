"""replays/router.py -- POST /replays, GET /replays/{id}."""

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
from app.replays import service
from app.replays.schemas import CreateReplayRequest, ReplayResponse

replays_router = APIRouter(prefix="/replays", tags=["replays"])
_settings = get_settings()


@replays_router.post("", response_model=ReplayResponse, status_code=202)
async def create_replay(
    req: CreateReplayRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ReplayResponse:
    """Create a replay job and enqueue it for async execution.

    Returns 202 Accepted with status=pending immediately.
    Poll GET /replays/{id} for progress.
    """
    replay = await service.create_replay(db, req, current_user.id)

    # Enqueue the arq job
    try:
        redis_settings = RedisSettings.from_dsn(_settings.redis_url)
        pool = await create_pool(redis_settings)
        await pool.enqueue_job("run_replay_job", str(replay.id))
        await pool.aclose()
    except Exception:
        pass

    return ReplayResponse.model_validate(replay)


@replays_router.get("/{replay_id}", response_model=ReplayResponse)
async def get_replay(
    replay_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ReplayResponse:
    """Poll or fetch the final result of a replay (ownership-scoped)."""
    replay = await service.get_replay(db, replay_id, current_user.id)
    return ReplayResponse.model_validate(replay)
