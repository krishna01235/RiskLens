"""alerts/router.py -- Risk budget configuration and alert list endpoints.

Routes:
  PUT  /portfolios/{id}/risk-budget   -> upsert budget (ownership-scoped)
  GET  /portfolios/{id}/risk-budget   -> fetch current budget
  GET  /alerts                        -> cursor-paginated alert list
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.database import get_db
from app.deps import get_current_user
from app.alerts import service
from app.alerts.schemas import (
    AlertListResponse,
    AlertResponse,
    RiskBudgetResponse,
    RiskBudgetUpsertRequest,
)

alerts_router = APIRouter(tags=["alerts"])


@alerts_router.put(
    "/portfolios/{portfolio_id}/risk-budget",
    response_model=RiskBudgetResponse,
)
async def upsert_risk_budget(
    portfolio_id: uuid.UUID,
    req: RiskBudgetUpsertRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> RiskBudgetResponse:
    """Create or update the risk budget thresholds for a portfolio."""
    budget = await service.upsert_risk_budget(db, portfolio_id, current_user.id, req)
    return RiskBudgetResponse.model_validate(budget)


@alerts_router.get(
    "/portfolios/{portfolio_id}/risk-budget",
    response_model=RiskBudgetResponse | None,
)
async def get_risk_budget(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> RiskBudgetResponse | None:
    """Return the risk budget for a portfolio, or null if none configured."""
    budget = await service.get_risk_budget(db, portfolio_id, current_user.id)
    if budget is None:
        return None
    return RiskBudgetResponse.model_validate(budget)


@alerts_router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    portfolio_id: uuid.UUID | None = Query(default=None),
    cursor: datetime | None = Query(default=None, description="ISO datetime for keyset pagination"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> AlertListResponse:
    """Cursor-paginated alert list scoped to the requesting user."""
    items = await service.get_alerts(
        db, current_user.id, portfolio_id=portfolio_id, cursor=cursor, limit=limit
    )
    next_cursor = items[-1].fired_at.isoformat() if len(items) == limit else None
    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        next_cursor=next_cursor,
    )
