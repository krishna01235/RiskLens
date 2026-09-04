"""alerts/service.py -- Business logic for risk budgets and alerts.

Ownership enforced on every operation:
  - Risk budget reads/writes scoped to portfolio owner.
  - Alert list scoped to portfolio owner.
  - No raw SQL string updates; explicit model mutations only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert
from app.alerts.schemas import RiskBudgetUpsertRequest
from app.portfolios.models import Portfolio, RiskBudget


async def _assert_portfolio_owned(
    db: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")


async def upsert_risk_budget(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    req: RiskBudgetUpsertRequest,
) -> RiskBudget:
    """Create or update the risk budget for a portfolio (ownership-scoped)."""
    await _assert_portfolio_owned(db, portfolio_id, user_id)

    result = await db.execute(
        select(RiskBudget).where(RiskBudget.portfolio_id == portfolio_id)
    )
    budget = result.scalar_one_or_none()

    if budget is None:
        budget = RiskBudget(
            portfolio_id=portfolio_id,
            max_cvar=Decimal(str(req.max_cvar)),
            watch_threshold=Decimal(str(req.watch_threshold)),
            high_threshold=Decimal(str(req.high_threshold)),
            breach_threshold=Decimal(str(req.breach_threshold)),
            updated_at=datetime.now(UTC),
        )
        db.add(budget)
    else:
        budget.max_cvar = Decimal(str(req.max_cvar))
        budget.watch_threshold = Decimal(str(req.watch_threshold))
        budget.high_threshold = Decimal(str(req.high_threshold))
        budget.breach_threshold = Decimal(str(req.breach_threshold))
        budget.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(budget)
    return budget


async def get_risk_budget(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RiskBudget | None:
    """Return the risk budget for a portfolio, or None if not configured."""
    await _assert_portfolio_owned(db, portfolio_id, user_id)
    result = await db.execute(
        select(RiskBudget).where(RiskBudget.portfolio_id == portfolio_id)
    )
    return result.scalar_one_or_none()


async def get_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    cursor: datetime | None = None,
    limit: int = 50,
) -> list[Alert]:
    """Return alerts for the requesting user, scoped by portfolio if given.

    Uses keyset pagination on fired_at (descending).
    Ownership enforced via JOIN on portfolios.user_id.
    """
    query = (
        select(Alert)
        .join(Portfolio, Portfolio.id == Alert.portfolio_id)
        .where(Portfolio.user_id == user_id)
        .order_by(Alert.fired_at.desc())
        .limit(limit)
    )
    if portfolio_id is not None:
        query = query.where(Alert.portfolio_id == portfolio_id)
    if cursor is not None:
        query = query.where(Alert.fired_at < cursor)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_latest_decision(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Decision | None:
    """Return the latest decision generated for this portfolio."""
    from app.alerts.models import Decision
    await _assert_portfolio_owned(db, portfolio_id, user_id)
    query = (
        select(Decision)
        .join(Alert, Alert.id == Decision.alert_id)
        .where(Alert.portfolio_id == portfolio_id)
        .order_by(Decision.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()
