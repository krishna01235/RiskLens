"""
quant/risk_metrics.py — Core portfolio risk metrics.

Formulas (matching docs/implementation.md §F5 / §F11 notation):

  Portfolio volatility:
    σ_p = sqrt(w^T · Σ · w)

  Historical VaR at confidence level α (e.g. 0.95):
    VaR_α = -quantile(r_p, 1-α)
    (positive number representing a loss; the (1-α) worst fraction of outcomes)

  Historical CVaR (Expected Shortfall) at confidence level α:
    CVaR_α = -E[ r_p | r_p ≤ -VaR_α ]

  Sharpe ratio (annualised, 252 trading days):
    S = (μ_p - r_f) / σ_p * sqrt(252)
    where μ_p = mean daily log-return, r_f = daily risk-free rate

  Max drawdown:
    MDD = max over t of (peak_t - r_p_cumulative_t) / peak_t
    where peak_t = max(cumulative_return_{0..t})

  Marginal risk contribution (MCR):
    MCR_i = (Σ · w)_i / σ_p

  Risk contribution (RC):
    RC_i = w_i · MCR_i
    (invariant: sum_i(RC_i) = σ_p)

All functions take plain NumPy/Pandas — no I/O, no FastAPI, no DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import json

from quant.covariance import InsufficientDataError

MIN_OBSERVATIONS = 20  # shared constant
ANNUALISATION_FACTOR = 252  # trading days per year
_DRAWDOWN_TOLERANCE = 1e-10  # avoid division by near-zero peaks


# ── Data containers ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RiskContribution:
    """Per-asset risk contribution decomposition."""

    symbol: str
    weight: float  # portfolio weight w_i
    mcr: float  # marginal contribution to risk MCR_i
    rc: float  # absolute risk contribution RC_i = w_i * MCR_i
    rc_pct: float  # fraction of total volatility: RC_i / σ_p


@dataclass(frozen=True)
class RiskEstimate:
    """Full risk estimate for a portfolio at a point in time."""

    volatility: float  # annualised portfolio volatility σ_p * sqrt(252)
    var_95: float  # 1-day 95% historical VaR (positive = loss)
    cvar_95: float  # 1-day 95% historical CVaR (positive = loss)
    sharpe: float | None  # annualised Sharpe ratio; None if r_f unavailable
    max_drawdown: float  # maximum drawdown fraction (positive = loss)
    risk_contributions: list[RiskContribution] = field(default_factory=list)
    n_obs: int = 0  # number of observations used
    insufficient_data: bool = False  # True when result is unreliable


# ── Internal helpers ───────────────────────────────────────────────────────────


def _check_min_obs(n: int, label: str = "risk estimate") -> None:
    """Raise InsufficientDataError if n < MIN_OBSERVATIONS."""
    if n < MIN_OBSERVATIONS:
        raise InsufficientDataError(
            f"{label} requires at least {MIN_OBSERVATIONS} observations; got {n}."
        )


# ── Public API ─────────────────────────────────────────────────────────────────


def compute_volatility(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
) -> float:
    """
    Compute annualised portfolio volatility.

    σ_p = sqrt(w^T · Σ · w) * sqrt(252)

    Parameters
    ----------
    weights:
        1-D array of portfolio weights; must sum to ~1.
    cov_matrix:
        (N, N) covariance matrix (daily returns scale).

    Returns
    -------
    Annualised volatility (positive float).
    """
    daily_var = float(weights @ cov_matrix @ weights)
    # Protect against tiny floating-point negatives from imperfect matrices.
    daily_var = max(daily_var, 0.0)
    return float(np.sqrt(daily_var) * np.sqrt(ANNUALISATION_FACTOR))


def compute_var_cvar(
    portfolio_returns: pd.Series | np.ndarray,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Compute historical (non-parametric) VaR and CVaR.

    VaR_α   = -quantile(r_p, 1-α)   [loss expressed as positive number]
    CVaR_α  = -mean(r_p[r_p ≤ -VaR_α])

    Parameters
    ----------
    portfolio_returns:
        Array of daily portfolio returns (log or simple, same scale).
    confidence:
        Confidence level, e.g. 0.95 for 95% VaR/CVaR.

    Returns
    -------
    (VaR, CVaR) as positive numbers representing losses.

    Raises
    ------
    InsufficientDataError if len(portfolio_returns) < MIN_OBSERVATIONS.
    ValueError if no returns fall below the VaR threshold (degenerate).
    """
    r = np.asarray(portfolio_returns, dtype=float)
    r = r[~np.isnan(r)]
    _check_min_obs(len(r), label="VaR/CVaR")

    var = float(-np.percentile(r, (1 - confidence) * 100))
    tail = r[r <= -var]
    if len(tail) == 0:
        # Degenerate: all returns above the threshold — CVaR = VaR.
        cvar = var
    else:
        cvar = float(-np.mean(tail))

    return var, cvar


def compute_sharpe(
    portfolio_returns: pd.Series | np.ndarray,
    risk_free_daily: float = 0.0,
) -> float:
    """
    Compute annualised Sharpe ratio.

    S = (μ_p - r_f) / σ_daily * sqrt(252)

    Parameters
    ----------
    portfolio_returns:
        Array of daily portfolio returns.
    risk_free_daily:
        Daily risk-free rate (default 0 for simplicity; pass 0.05/252 for ~5% annual).

    Returns
    -------
    Annualised Sharpe ratio (can be negative).

    Raises
    ------
    InsufficientDataError if fewer than MIN_OBSERVATIONS observations.
    """
    r = np.asarray(portfolio_returns, dtype=float)
    r = r[~np.isnan(r)]
    _check_min_obs(len(r), label="Sharpe ratio")

    excess = r - risk_free_daily
    std = float(np.std(excess, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(ANNUALISATION_FACTOR))


def compute_max_drawdown(
    portfolio_returns: pd.Series | np.ndarray,
) -> float:
    """
    Compute maximum drawdown of the cumulative return series.

    MDD = max_t( (peak_t - cum_t) / peak_t )

    Parameters
    ----------
    portfolio_returns:
        Array of daily portfolio returns (log or simple).

    Returns
    -------
    Max drawdown as a positive fraction (e.g. 0.35 = 35% drawdown).

    Raises
    ------
    InsufficientDataError if fewer than MIN_OBSERVATIONS observations.
    """
    r = np.asarray(portfolio_returns, dtype=float)
    r = r[~np.isnan(r)]
    _check_min_obs(len(r), label="max drawdown")

    cum = np.cumprod(1 + r)  # works for simple returns; close enough for log returns
    running_peak = np.maximum.accumulate(cum)
    # Avoid division by near-zero running peaks at t=0.
    safe_peak = np.where(running_peak < _DRAWDOWN_TOLERANCE, 1.0, running_peak)
    drawdowns = (running_peak - cum) / safe_peak
    return float(np.max(drawdowns))


def compute_risk_contribution(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    symbols: list[str],
) -> list[RiskContribution]:
    """
    Compute per-asset marginal and absolute risk contributions.

    MCR_i = (Σ · w)_i / σ_p
    RC_i  = w_i · MCR_i
    (invariant: sum_i(RC_i) = σ_p)

    Parameters
    ----------
    weights:
        1-D array of portfolio weights (same ordering as ``symbols``).
    cov_matrix:
        (N, N) daily covariance matrix.
    symbols:
        List of asset names, aligned with the weight array.

    Returns
    -------
    List of RiskContribution objects, one per asset.
    RC percentages (rc_pct) sum to 1.0.

    Raises
    ------
    ValueError if len(weights) != len(symbols) or portfolio volatility is zero.
    """
    if len(weights) != len(symbols):
        raise ValueError(
            f"len(weights)={len(weights)} must equal len(symbols)={len(symbols)}."
        )

    sigma_p_daily = float(np.sqrt(max(weights @ cov_matrix @ weights, 0.0)))
    if sigma_p_daily == 0.0:
        raise ValueError(
            "Portfolio daily volatility is zero; risk contribution is undefined."
        )

    # MCR: gradient of portfolio volatility w.r.t. each weight.
    # (Σ · w) / σ_p  — each element is in return-scale (daily).
    mcr_vec = (cov_matrix @ weights) / sigma_p_daily

    result: list[RiskContribution] = []
    for i, sym in enumerate(symbols):
        rc_i = float(weights[i] * mcr_vec[i])
        result.append(
            RiskContribution(
                symbol=sym,
                weight=float(weights[i]),
                mcr=float(mcr_vec[i]),
                rc=rc_i,
                rc_pct=rc_i / sigma_p_daily,
            )
        )
    return result


def assemble_volatility_vector(
    cov_matrix: np.ndarray,
    symbols: list[str],
    garch_payloads: dict[str, str | None],
) -> np.ndarray:
    """
    Assemble the daily volatility vector for Monte Carlo simulation.

    Reads GARCH volatility from JSON payloads if available and valid.
    Falls back to the historical standard deviation (sqrt of covariance diagonal)
    otherwise.

    Parameters
    ----------
    cov_matrix:
        (N, N) daily covariance matrix.
    symbols:
        List of asset names.
    garch_payloads:
        Dictionary mapping symbol to its JSON payload string from Redis,
        e.g., '{"volatility": 0.05, "source": "garch", "updated_at": 1690000000.0}'.
        Values can be None if not found in Redis.

    Returns
    -------
    1-D array of daily volatilities aligned with ``symbols``.
    """
    vol_vec = np.zeros(len(symbols), dtype=float)
    hist_vols = np.sqrt(np.maximum(np.diag(cov_matrix), 0.0))

    for i, sym in enumerate(symbols):
        payload_str = garch_payloads.get(sym)
        vol = None
        if payload_str:
            try:
                data = json.loads(payload_str)
                if "volatility" in data:
                    vol = float(data["volatility"])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        if vol is not None:
            vol_vec[i] = vol
        else:
            vol_vec[i] = float(hist_vols[i])
            
    return vol_vec


def compute_risk_estimate(
    portfolio_returns: pd.Series,
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    symbols: list[str],
    confidence: float = 0.95,
    risk_free_daily: float = 0.0,
) -> RiskEstimate:
    """
    Compute the full risk estimate for a portfolio.

    This is the main entry point for the slow-path worker (Phase 10).
    All individual metric functions are composed here.

    Parameters
    ----------
    portfolio_returns:
        Daily portfolio return series.
    weights:
        1-D array of portfolio weights aligned with ``symbols``.
    cov_matrix:
        (N, N) daily covariance matrix (Ledoit-Wolf output).
    symbols:
        Asset names, aligned with weight vector.
    confidence:
        VaR/CVaR confidence level (default 0.95).
    risk_free_daily:
        Daily risk-free rate for Sharpe calculation (default 0).

    Returns
    -------
    RiskEstimate.  If insufficient data, returns a RiskEstimate with
    ``insufficient_data=True`` and all metrics set to 0 rather than
    raising — callers should surface this state explicitly in the UI.
    """
    r = np.asarray(portfolio_returns.dropna(), dtype=float)
    n = len(r)

    if n < MIN_OBSERVATIONS:
        return RiskEstimate(
            volatility=0.0,
            var_95=0.0,
            cvar_95=0.0,
            sharpe=None,
            max_drawdown=0.0,
            risk_contributions=[],
            n_obs=n,
            insufficient_data=True,
        )

    vol = compute_volatility(weights, cov_matrix)
    var_95, cvar_95 = compute_var_cvar(r, confidence=confidence)
    sharpe = compute_sharpe(r, risk_free_daily=risk_free_daily)
    mdd = compute_max_drawdown(r)

    try:
        rcs = compute_risk_contribution(weights, cov_matrix, symbols)
    except ValueError:
        rcs = []

    return RiskEstimate(
        volatility=vol,
        var_95=float(var_95),
        cvar_95=float(cvar_95),
        sharpe=float(sharpe),
        max_drawdown=float(mdd),
        risk_contributions=rcs,
        n_obs=n,
        insufficient_data=False,
    )


def cov_to_corr(cov_matrix: np.ndarray) -> np.ndarray:
    """
    Convert a covariance matrix to a correlation matrix.
    
    cor(i, j) = cov(i, j) / (std_i * std_j)
    """
    v = np.sqrt(np.maximum(np.diag(cov_matrix), 0.0))
    outer_v = np.outer(v, v)
    # Prevent division by zero if an asset has zero variance
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = cov_matrix / outer_v
    corr[np.isinf(corr)] = 0.0
    corr[np.isnan(corr)] = 0.0
    # Ensure diagonal is exactly 1.0
    np.fill_diagonal(corr, 1.0)
    return corr


def detect_correlation_clusters(
    corr_matrix: np.ndarray,
    symbols: list[str],
    threshold: float = 0.7,
) -> list[list[str]]:
    """
    Identify clusters of highly correlated assets.
    
    Returns a list of clusters (lists of symbols) where each asset in a cluster
    is correlated > threshold with at least one other asset in the cluster
    (connected components of the correlation graph thresholded at `threshold`).
    
    Parameters
    ----------
    corr_matrix:
        (N, N) correlation matrix.
    symbols:
        List of asset names.
    threshold:
        Correlation threshold (default 0.7).
        
    Returns
    -------
    List of symbol lists, e.g. [["NVDA", "AMD", "INTC"], ["XOM", "CVX"]]
    Single-item clusters are filtered out (returns only clusters size >= 2).
    """
    n = len(symbols)
    if n < 2:
        return []
        
    visited = set()
    clusters: list[list[str]] = []
    
    # Simple BFS/DFS to find connected components
    for i in range(n):
        if i in visited:
            continue
            
        cluster_indices = [i]
        visited.add(i)
        
        # BFS queue
        queue = [i]
        while queue:
            curr = queue.pop(0)
            for j in range(n):
                if j not in visited and curr != j:
                    if corr_matrix[curr, j] > threshold:
                        visited.add(j)
                        cluster_indices.append(j)
                        queue.append(j)
                        
        if len(cluster_indices) > 1:
            clusters.append([symbols[idx] for idx in sorted(cluster_indices)])
            
    return clusters

