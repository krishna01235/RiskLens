"""
quant/covariance.py — Ledoit-Wolf covariance estimation with fallback.

Formula (matching docs/implementation.md §F6):
  The Ledoit-Wolf shrinkage estimator Σ̂_LW = (1-α)·S + α·μ·I
  where S is the sample covariance, α is the optimal shrinkage coefficient,
  and μ = tr(S)/N is the shrinkage target (scaled identity).

  sklearn.covariance.LedoitWolf computes this automatically.

Edge cases:
  - Fewer than MIN_OBSERVATIONS rows → InsufficientDataError raised;
    callers must handle this and surface an explicit UI state.
  - Post-fit matrix must be positive-semidefinite; verified by checking
    all eigenvalues ≥ -TOL (see assertion in estimate_covariance).
  - If sklearn fitting still fails (numerical edge case), fallback to
    a diagonal covariance matrix (historical variance only).

No I/O — takes plain NumPy/Pandas, returns NumPy arrays + metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

MIN_OBSERVATIONS = 20  # below this we cannot trust any covariance estimator
_PSD_TOL = 1e-8  # tolerance for positive-semidefiniteness check


class InsufficientDataError(Exception):
    """Raised when there are too few observations to estimate covariance."""


@dataclass(frozen=True)
class CovarianceResult:
    """Result of a covariance estimation."""

    matrix: np.ndarray  # shape (N, N)
    symbols: list[str]  # column ordering matching matrix rows/cols
    estimator: str  # 'ledoit_wolf' | 'diagonal_fallback'
    n_obs: int  # number of observations used


def estimate_covariance(
    returns: pd.DataFrame,
) -> CovarianceResult:
    """
    Estimate the covariance matrix of asset returns using Ledoit-Wolf shrinkage.

    Parameters
    ----------
    returns:
        DataFrame of shape (T, N), columns = symbol names.
        Each column is a return series; rows are time observations.
        Rows with any NaN are dropped before fitting.

    Returns
    -------
    CovarianceResult with a positive-semidefinite (N, N) matrix.

    Raises
    ------
    InsufficientDataError
        If the cleaned returns DataFrame has fewer than MIN_OBSERVATIONS rows.
    """
    clean = returns.dropna(how="any")
    n_obs, n_assets = clean.shape
    symbols = list(clean.columns)

    if n_obs < MIN_OBSERVATIONS:
        raise InsufficientDataError(
            f"Covariance estimation requires at least {MIN_OBSERVATIONS} complete "
            f"observations; got {n_obs}.  Surface 'insufficient data' in the UI."
        )

    X = clean.to_numpy(dtype=float)

    try:
        lw = LedoitWolf().fit(X)
        cov = lw.covariance_
        estimator = "ledoit_wolf"
    except Exception:
        # Numerical edge case: fall back to diagonal (historical variance).
        # This should be extremely rare with Ledoit-Wolf, but we must never crash.
        cov = np.diag(np.var(X, axis=0, ddof=1))
        estimator = "diagonal_fallback"

    # Verify the result is positive-semidefinite (eigenvalues ≥ -TOL).
    min_eigval = float(np.linalg.eigvalsh(cov).min())
    if min_eigval < -_PSD_TOL:
        # If LW somehow failed PSD check, fall back to diagonal.
        cov = np.diag(np.var(X, axis=0, ddof=1))
        estimator = "diagonal_fallback"

    return CovarianceResult(
        matrix=cov,
        symbols=symbols,
        estimator=estimator,
        n_obs=n_obs,
    )


def covariance_to_correlation(cov: np.ndarray) -> np.ndarray:
    """
    Convert a covariance matrix to a correlation matrix.

    Formula: ρ_{ij} = σ_{ij} / (σ_i · σ_j)

    Parameters
    ----------
    cov:
        Square, positive-semidefinite covariance matrix.

    Returns
    -------
    Correlation matrix of the same shape, values in [-1, 1].
    """
    std = np.sqrt(np.diag(cov))
    # Guard against zero-variance assets (degenerate case).
    std = np.where(std == 0, 1.0, std)
    corr = cov / np.outer(std, std)
    # Clip to [-1, 1] for numerical hygiene.
    return np.clip(corr, -1.0, 1.0)
