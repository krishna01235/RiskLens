"""
quant/returns.py — Return-series utilities.

Formulas (matching docs/implementation.md notation):
  Simple return:  r_t = (P_t - P_{t-1}) / P_{t-1}
  Log return:     r_t = ln(P_t / P_{t-1})
  Portfolio log return: r_p,t = sum_i( w_i * r_i,t )
    where w_i = (quantity_i * avg_price_i) / total_portfolio_value
    (buy-and-hold weights normalised from cost basis, NOT rebalanced daily)

No I/O inside this module — all functions take plain NumPy/Pandas structures.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Data containers ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReturnSeries:
    """Wraps a computed return DataFrame with metadata."""

    values: pd.DataFrame  # shape (T, N), columns = symbol names
    kind: str  # 'simple' | 'log'
    min_obs: int  # number of valid observations (smallest column)


@dataclass(frozen=True)
class PortfolioReturnSeries:
    """Portfolio-level return series with per-asset weights."""

    values: pd.Series  # shape (T,), name = 'portfolio'
    weights: dict[str, float]  # symbol -> fraction (sum ≈ 1)


# ── Core functions ─────────────────────────────────────────────────────────────

MIN_OBSERVATIONS = 20  # below this, downstream estimators must not trust results


def compute_returns(
    prices: pd.DataFrame,
    kind: str = "log",
) -> ReturnSeries:
    """
    Compute per-asset return series from a price DataFrame.

    Parameters
    ----------
    prices:
        DataFrame with shape (T, N), columns = symbol names,
        index = sorted datetime (ascending).  Must have at least 2 rows.
    kind:
        'log' (default) or 'simple'.

    Returns
    -------
    ReturnSeries with shape (T-1, N).

    Raises
    ------
    ValueError if ``prices`` has fewer than 2 rows or ``kind`` is unknown.
    """
    if len(prices) < 2:
        raise ValueError(
            f"Need at least 2 price observations to compute returns; got {len(prices)}."
        )
    if kind not in ("log", "simple"):
        raise ValueError(f"Unknown return kind {kind!r}; expected 'log' or 'simple'.")

    if kind == "log":
        # r_t = ln(P_t) - ln(P_{t-1})
        rets = np.log(prices).diff().iloc[1:]
    else:
        # r_t = (P_t - P_{t-1}) / P_{t-1}
        rets = prices.pct_change().iloc[1:]

    min_obs = int(rets.notna().all(axis=1).sum())
    return ReturnSeries(values=rets, kind=kind, min_obs=min_obs)


def compute_weights(holdings: dict[str, tuple[float, float]]) -> dict[str, float]:
    """
    Compute portfolio weights from holdings cost-basis.

    Parameters
    ----------
    holdings:
        Mapping of symbol -> (quantity, average_price).

    Returns
    -------
    Mapping of symbol -> weight (0 < w_i <= 1, sum = 1).

    Raises
    ------
    ValueError if holdings is empty or any quantity/price is non-positive.
    """
    if not holdings:
        raise ValueError("Holdings must not be empty.")

    market_values: dict[str, float] = {}
    for symbol, (qty, avg_price) in holdings.items():
        if qty <= 0 or avg_price <= 0:
            raise ValueError(
                f"Quantity and average_price must be positive; "
                f"got symbol={symbol!r}, quantity={qty}, average_price={avg_price}."
            )
        market_values[symbol] = qty * avg_price

    total = sum(market_values.values())
    return {sym: mv / total for sym, mv in market_values.items()}


def compute_portfolio_returns(
    asset_returns: ReturnSeries,
    weights: dict[str, float],
) -> PortfolioReturnSeries:
    """
    Compute the portfolio log-return series as a weighted sum of asset returns.

    Formula: r_p,t = sum_i( w_i * r_i,t )

    Parameters
    ----------
    asset_returns:
        Output of :func:`compute_returns`.
    weights:
        Mapping of symbol -> weight (from :func:`compute_weights`).
        All symbols must appear in ``asset_returns.values.columns``.

    Returns
    -------
    PortfolioReturnSeries.

    Raises
    ------
    ValueError if a symbol in weights is missing from asset_returns.
    """
    missing = set(weights) - set(asset_returns.values.columns)
    if missing:
        raise ValueError(
            f"Symbols in weights not found in asset_returns: {missing!r}."
        )

    w_series = pd.Series(weights, dtype=float)
    # Align columns to weight order then dot-product
    aligned = asset_returns.values[list(weights.keys())]
    portfolio_rets = aligned.dot(w_series).rename("portfolio")
    return PortfolioReturnSeries(values=portfolio_rets, weights=weights)
