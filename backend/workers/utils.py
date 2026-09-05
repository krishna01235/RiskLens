"""workers/utils.py -- Shared worker utilities."""

import json
import numpy as np
import pandas as pd
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis

from app.portfolios.models import Portfolio, Holding
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.monte_carlo import SimulationParams
from quant.returns import (
    ReturnSeries,
    compute_portfolio_returns,
    compute_returns,
    compute_weights,
)

async def build_simulation_params(
    portfolio_id: str,
    num_paths: int,
    horizon_days: int,
    db: AsyncSession,
    redis: Redis,
) -> Tuple[SimulationParams, np.ndarray | None]:
    """Load holdings + price history to build SimulationParams."""
    import uuid
    portfolio_result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .where(Portfolio.id == uuid.UUID(portfolio_id))
    )
    portfolio = portfolio_result.scalar_one_or_none()
    if portfolio is None:
        raise ValueError(f"Portfolio {portfolio_id} not found.")

    holdings: dict[str, tuple[float, float]] = {}
    for h in portfolio.holdings:
        holdings[str(h.symbol)] = (float(h.quantity), float(h.average_price))

    if not holdings:
        raise ValueError("Portfolio has no holdings to simulate.")

    symbols = list(holdings.keys())
    weights_dict = compute_weights(holdings)
    weights = np.array([weights_dict[s] for s in symbols], dtype=float)

    total_value = sum(qty * price for qty, price in holdings.values())
    current_values = np.array(
        [weights_dict[s] * total_value for s in symbols], dtype=float
    )

    garch_vols: dict[int, float] = {}
    for i, sym in enumerate(symbols):
        raw = await redis.get(f"symbol_volatility:{sym}")
        if raw is not None:
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    vol = float(data.get("annualised_vol", 0))
                else:
                    vol = float(data)
                if vol > 0:
                    garch_vols[i] = vol
            except (ValueError, TypeError):
                pass

    history: dict[str, dict[str, str]] = {}
    for sym in symbols:
        closes = await redis.hgetall(f"price_history:{sym}")
        if closes:
            history[sym] = dict(closes)

    frame = {}
    for sym, closes in history.items():
        frame[sym] = pd.Series({d: float(v) for d, v in closes.items()})
    prices = pd.DataFrame(frame) if frame else pd.DataFrame()
    if not prices.empty:
        prices = prices.sort_index()

    portfolio_returns = None
    n = len(symbols)
    placeholder_daily_sigma = 0.02
    cov_matrix = np.diag([placeholder_daily_sigma**2] * n)
    mean_daily_returns = np.zeros(n)

    if len(prices) >= 2:
        try:
            returns_df: ReturnSeries = compute_returns(prices, kind="log")
            cov_result = estimate_covariance(returns_df.values)
            
            aligned_symbols = cov_result.symbols
            weights_map = {s: holdings[s] for s in aligned_symbols}
            aligned_weights = compute_weights(weights_map)
            port_ret = compute_portfolio_returns(returns_df, aligned_weights)
            portfolio_returns = port_ret.values.to_numpy()
            
            symbols = aligned_symbols
            weights = np.array([aligned_weights[s] for s in symbols], dtype=float)
            current_values = np.array([aligned_weights[s] * total_value for s in symbols], dtype=float)
            mean_daily_returns = np.mean(returns_df.values.to_numpy(), axis=0)
            cov_matrix = cov_result.matrix
        except (ValueError, InsufficientDataError):
            pass

    params = SimulationParams(
        num_paths=num_paths,
        horizon_days=horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
    )
    return params, portfolio_returns
