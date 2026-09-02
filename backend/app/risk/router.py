"""risk/router.py — Portfolio risk endpoints (§7.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.database import get_db
from app.deps import get_current_user, get_redis
from app.risk import service
from app.risk.schemas import RiskResponse

risk_router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@risk_router.get("/{portfolio_id}/risk", response_model=RiskResponse)
async def get_portfolio_risk(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis: Redis = Depends(get_redis),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> RiskResponse:
    """Return the cached risk state for a user-owned portfolio.

    REST fallback for non-WS clients (e.g. the Slack bot) and for the initial
    page load of the dashboard.
    """
    return await service.get_portfolio_risk(db, redis, portfolio_id, current_user.id)
