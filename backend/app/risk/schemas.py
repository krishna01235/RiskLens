"""risk/schemas.py — Pydantic request/response models for the risk API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class RiskMetrics(BaseModel):
    """Core risk metric block.

    VaR/CVaR are stored as positive loss numbers per quant/risk_metrics.py.
    """

    var_95: float
    cvar_95: float
    volatility: float
    sharpe: float | None
    max_drawdown: float
    n_obs: int


class RiskContributionOut(BaseModel):
    """Per-asset risk contribution decomposition (Phase 15 surfaces this)."""

    symbol: str
    weight: float
    mcr: float
    rc: float
    rc_pct: float


class RiskResponse(BaseModel):
    """Cached risk state for one portfolio.

    data_status is one of ``pending`` / ``ready`` / ``insufficient_data``.
    """

    portfolio_id: uuid.UUID
    data_status: str
    metrics: RiskMetrics | None = None
    risk_contributions: list[RiskContributionOut] = []
    portfolio_value: str | None = None
    daily_pnl: str | None = None
    risk_updated_at: float | None = None
