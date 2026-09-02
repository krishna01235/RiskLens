"""
quant/monte_carlo.py -- Vectorized GBM Monte Carlo with antithetic variates.

Mathematics:
  For each asset i over horizon T (trading days):
    S_i,T = S_i,0 * exp((mu_i - 0.5 * sigma_i^2) * T + sigma_i * sqrt(T) * Z_i)
  where Z ~ N(0, I) are correlated via Cholesky: Z = L @ eps, eps ~ N(0, I).

  Antithetic variates: generate N/2 independent eps, pair with -eps -> N total paths.
  GARCH volatility scaling: when per-asset GARCH sigma forecasts are provided,
  the covariance matrix diagonal is overridden before Cholesky decomposition.

No I/O in this module -- all functions accept plain NumPy/dict structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

# -- Constants ----------------------------------------------------------------

TRADING_DAYS_PER_YEAR = 252
_MIN_PATHS = 100


# -- Data containers ----------------------------------------------------------


@dataclass(frozen=True)
class SimulationParams:
    """All inputs needed to run one Monte Carlo simulation.

    Attributes
    ----------
    num_paths : int
        Total number of paths. Must be >= 100. Made even internally.
    horizon_days : int
        Simulation horizon in trading days (1, 7, 30, 90).
    weights : np.ndarray
        Shape (N,), portfolio weights summing to ~1.
    current_values : np.ndarray
        Shape (N,), current position values (S_0 per asset).
    mean_daily_returns : np.ndarray
        Shape (N,), estimated daily mean log returns.
    cov_matrix : np.ndarray
        (N, N) daily Ledoit-Wolf covariance matrix.
    garch_vols : dict[int, float]
        Optional {asset_index: annualised_garch_vol}. Overrides cov diagonal.
    symbols : list[str]
        Asset names aligned with arrays (for error messages).
    """

    num_paths: int
    horizon_days: int
    weights: np.ndarray
    current_values: np.ndarray
    mean_daily_returns: np.ndarray
    cov_matrix: np.ndarray
    garch_vols: dict[int, float] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SimulationResult:
    """Output of a Monte Carlo simulation run.

    Attributes
    ----------
    prob_profit : float
        Fraction of paths with positive terminal P&L.
    prob_loss : float
        Fraction of paths with negative terminal P&L.
    expected_pnl : float
        Mean terminal P&L across all paths.
    pnl_p5, pnl_p50, pnl_p95 : float
        5th, 50th, 95th percentile of terminal P&L.
    terminal_pnl : np.ndarray
        Full per-path P&L array, shape (num_paths,). Kept for EVT (Phase 13).
    num_paths : int
        Actual paths run (may be adjusted to even).
    """

    prob_profit: float
    prob_loss: float
    expected_pnl: float
    pnl_p5: float
    pnl_p50: float
    pnl_p95: float
    terminal_pnl: np.ndarray
    num_paths: int


# -- Internal helpers ---------------------------------------------------------


def _validate_params(params: SimulationParams) -> None:
    n = len(params.weights)
    if n == 0:
        raise ValueError("weights must be non-empty.")
    if params.cov_matrix.shape != (n, n):
        raise ValueError(
            f"cov_matrix shape {params.cov_matrix.shape} must be ({n}, {n})."
        )
    if len(params.mean_daily_returns) != n:
        raise ValueError(
            f"mean_daily_returns length {len(params.mean_daily_returns)} must equal "
            f"len(weights) = {n}."
        )
    if len(params.current_values) != n:
        raise ValueError(
            f"current_values length {len(params.current_values)} must equal "
            f"len(weights) = {n}."
        )
    if params.num_paths < _MIN_PATHS:
        raise ValueError(
            f"num_paths={params.num_paths} is too small; minimum is {_MIN_PATHS}."
        )
    if params.horizon_days < 1:
        raise ValueError(f"horizon_days must be >= 1; got {params.horizon_days}.")


def _apply_garch_scaling(
    cov: np.ndarray,
    garch_vols: dict[int, float],
) -> np.ndarray:
    """Override covariance diagonal with GARCH forecast volatility.

    Annual GARCH vols are converted to daily scale (/ sqrt(252)) before
    replacing the diagonal. Off-diagonals are rescaled to preserve correlations.
    """
    if not garch_vols:
        return cov

    n = cov.shape[0]
    diag_std = np.sqrt(np.maximum(np.diag(cov), 0.0))
    new_std = diag_std.copy()
    for idx, ann_vol in garch_vols.items():
        if 0 <= idx < n:
            new_std[idx] = ann_vol / np.sqrt(TRADING_DAYS_PER_YEAR)

    safe_std = np.where(diag_std == 0, 1.0, diag_std)
    corr = cov / np.outer(safe_std, safe_std)
    return corr * np.outer(new_std, new_std)


def _cholesky_safe(cov: np.ndarray) -> np.ndarray:
    """Cholesky decomposition with small jitter fallback for near-singular matrices."""
    try:
        return np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        n = cov.shape[0]
        jitter = np.eye(n) * 1e-8 * max(abs(np.diag(cov)).mean(), 1e-10)
        return np.linalg.cholesky(cov + jitter)


def _simulate_paths(
    num_paths: int,
    T: int,
    mu: np.ndarray,
    S0: np.ndarray,
    cov: np.ndarray,
    garch_vols: dict[int, float],
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Core vectorized GBM path computation. Returns terminal P&L array."""
    if rng is None:
        rng = np.random.default_rng()

    num_paths = num_paths + (num_paths % 2)  # ensure even
    half = num_paths // 2
    n = len(mu)

    scaled_cov = _apply_garch_scaling(cov, garch_vols)
    L = _cholesky_safe(scaled_cov)

    daily_var = np.diag(scaled_cov)
    drift = (mu - 0.5 * daily_var) * T
    sqrt_T = np.sqrt(float(T))

    eps_half = rng.standard_normal((half, n))
    eps = np.concatenate([eps_half, -eps_half], axis=0)
    Z = eps @ L.T  # correlated shocks, shape (num_paths, n)

    log_returns = drift[np.newaxis, :] + sqrt_T * Z
    growth = np.exp(log_returns)
    terminal_pnl: np.ndarray = ((growth - 1.0) * S0[np.newaxis, :]).sum(axis=1)
    return terminal_pnl


# -- Public API ---------------------------------------------------------------


def run_simulation(params: SimulationParams) -> SimulationResult:
    """Run a full vectorized Monte Carlo simulation in one shot.

    Parameters
    ----------
    params : SimulationParams

    Returns
    -------
    SimulationResult

    Raises
    ------
    ValueError on bad input dimensions or insufficient paths.
    """
    _validate_params(params)
    num_paths = params.num_paths + (params.num_paths % 2)

    terminal_pnl = _simulate_paths(
        num_paths=params.num_paths,
        T=params.horizon_days,
        mu=np.asarray(params.mean_daily_returns, dtype=float),
        S0=np.asarray(params.current_values, dtype=float),
        cov=params.cov_matrix,
        garch_vols=params.garch_vols,
    )

    return SimulationResult(
        prob_profit=float(np.mean(terminal_pnl > 0.0)),
        prob_loss=float(np.mean(terminal_pnl < 0.0)),
        expected_pnl=float(np.mean(terminal_pnl)),
        pnl_p5=float(np.percentile(terminal_pnl, 5)),
        pnl_p50=float(np.percentile(terminal_pnl, 50)),
        pnl_p95=float(np.percentile(terminal_pnl, 95)),
        terminal_pnl=terminal_pnl,
        num_paths=num_paths,
    )


def run_simulation_batched(
    params: SimulationParams,
    batch_size: int = 10_000,
    progress_cb: Callable[[float], None] | None = None,
) -> SimulationResult:
    """Run simulation in batches, calling progress_cb(pct) after each batch.

    Identical math to run_simulation -- split for WS progress streaming.

    Parameters
    ----------
    params : SimulationParams
    batch_size : int
        Paths per batch. Smaller = more frequent progress updates.
    progress_cb : callable, optional
        Called with a float in [0.0, 1.0] after each batch.

    Returns
    -------
    SimulationResult
    """
    _validate_params(params)

    num_paths = params.num_paths + (params.num_paths % 2)
    half = num_paths // 2
    T = params.horizon_days
    n = len(params.weights)

    mu = np.asarray(params.mean_daily_returns, dtype=float)
    S0 = np.asarray(params.current_values, dtype=float)
    scaled_cov = _apply_garch_scaling(params.cov_matrix, params.garch_vols)
    L = _cholesky_safe(scaled_cov)
    daily_var = np.diag(scaled_cov)
    drift = (mu - 0.5 * daily_var) * T
    sqrt_T = np.sqrt(float(T))

    rng = np.random.default_rng()
    eps_half = rng.standard_normal((half, n))
    eps_all = np.concatenate([eps_half, -eps_half], axis=0)

    chunks: list[np.ndarray] = []
    paths_done = 0

    for start in range(0, num_paths, batch_size):
        end = min(start + batch_size, num_paths)
        eps_batch = eps_all[start:end]
        Z_batch = eps_batch @ L.T
        log_ret = drift[np.newaxis, :] + sqrt_T * Z_batch
        pnl_batch: np.ndarray = ((np.exp(log_ret) - 1.0) * S0[np.newaxis, :]).sum(axis=1)
        chunks.append(pnl_batch)
        paths_done += len(pnl_batch)
        if progress_cb is not None:
            progress_cb(paths_done / num_paths)

    terminal_pnl = np.concatenate(chunks)

    return SimulationResult(
        prob_profit=float(np.mean(terminal_pnl > 0.0)),
        prob_loss=float(np.mean(terminal_pnl < 0.0)),
        expected_pnl=float(np.mean(terminal_pnl)),
        pnl_p5=float(np.percentile(terminal_pnl, 5)),
        pnl_p50=float(np.percentile(terminal_pnl, 50)),
        pnl_p95=float(np.percentile(terminal_pnl, 95)),
        terminal_pnl=terminal_pnl,
        num_paths=num_paths,
    )
