"""risk/service.py — Read cached risk state for a portfolio.

Ownership is enforced at the service layer by reusing the portfolios service's
ownership gate (``_get_portfolio_owned``): a cross-user probe returns 403 and
a missing portfolio returns 404, exactly as for the holdings endpoints.
"""

from __future__ import annotations

import json
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolios.service import _get_portfolio_owned
from app.risk.schemas import RiskContributionOut, RiskMetrics, RiskResponse

_RISK_STATE_PREFIX = "risk_state:"


async def get_portfolio_risk(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RiskResponse:
    """Return the cached risk state for a user-owned portfolio.

    A missing fast-path/slow-path state (no ticks processed yet) is surfaced
    as ``data_status = "pending"`` so the UI can show a waiting state rather
    than a fabricated zero.
    """
    # Ownership gate BEFORE any data is read.
    await _get_portfolio_owned(db, portfolio_id, user_id)

    state = await redis.hgetall(f"{_RISK_STATE_PREFIX}{portfolio_id}")
    if not state:
        return RiskResponse(portfolio_id=portfolio_id, data_status="pending")

    risk_field = state.get("risk")
    if not risk_field:
        return RiskResponse(
            portfolio_id=portfolio_id,
            data_status="pending",
            portfolio_value=state.get("portfolio_value"),
            daily_pnl=state.get("daily_pnl"),
        )

    risk_data = json.loads(risk_field)
    metrics = risk_data.get("metrics")
    return RiskResponse(
        portfolio_id=portfolio_id,
        data_status=risk_data.get("data_status", "pending"),
        metrics=RiskMetrics(**metrics) if metrics else None,
        risk_contributions=[
            RiskContributionOut(**rc) for rc in risk_data.get("risk_contributions", [])
        ],
        portfolio_value=state.get("portfolio_value"),
        daily_pnl=state.get("daily_pnl"),
        risk_updated_at=risk_data.get("risk_updated_at"),
    )
