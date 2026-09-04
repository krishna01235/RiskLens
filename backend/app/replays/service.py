"""replays/service.py -- Business logic for replays."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.portfolios.models import Portfolio
from app.replays.models import Replay
from app.replays.schemas import CreateReplayRequest


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


async def create_replay(
    db: AsyncSession,
    req: CreateReplayRequest,
    user_id: uuid.UUID,
) -> Replay:
    """Create a replay row (status=pending)."""
    await _assert_portfolio_owned(db, req.portfolio_id, user_id)

    # Note: we might want rate limiting here similar to simulations, 
    # but for demo purposes, ownership is the primary gate.

    replay = Replay(
        portfolio_id=req.portfolio_id,
        period_key=req.period_key,
        status="pending",
    )
    db.add(replay)
    await db.commit()
    return await db.scalar(
        select(Replay)
        .options(selectinload(Replay.daily_states), selectinload(Replay.backtest_result))
        .where(Replay.id == replay.id)
    )


async def get_replay(
    db: AsyncSession, replay_id: uuid.UUID, user_id: uuid.UUID
) -> Replay:
    """Fetch a replay by id, scoped to the requesting user."""
    result = await db.execute(
        select(Replay)
        .join(Portfolio, Portfolio.id == Replay.portfolio_id)
        .options(
            selectinload(Replay.daily_states),
            selectinload(Replay.backtest_result),
        )
        .where(
            Replay.id == replay_id,
            Portfolio.user_id == user_id,
        )
    )
    replay = result.scalar_one_or_none()
    if replay is None:
        raise HTTPException(status_code=404, detail="Replay not found.")
    return replay
