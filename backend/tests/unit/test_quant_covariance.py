"""
tests/unit/test_quant_covariance.py

Unit tests for quant/covariance.py.

Key invariants tested:
  - Output is positive-semidefinite (all eigenvalues ≥ 0).
  - Diagonal entries equal variances.
  - Correlation matrix derived from covariance has diagonal exactly 1.0.
  - InsufficientDataError raised when n_obs < MIN_OBSERVATIONS (20).
  - Fallback to diagonal when sklearn fitting is unavailable (mocked).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.covariance import (
    MIN_OBSERVATIONS,
    CovarianceResult,
    InsufficientDataError,
    covariance_to_correlation,
    estimate_covariance,
)

# ── Fixtures ───────────────────────────────────────────────────────────────────


def _synthetic_returns(n: int = 60, assets: int = 3, seed: int = 42) -> pd.DataFrame:
    """Generate multivariate normal returns for testing."""
    rng = np.random.default_rng(seed)
    data = rng.normal(loc=0.001, scale=0.02, size=(n, assets))
    return pd.DataFrame(data, columns=[f"A{i}" for i in range(assets)])


# ── estimate_covariance ────────────────────────────────────────────────────────


class TestEstimateCovariance:
    def test_raises_on_insufficient_data(self):
        """
        Fewer than MIN_OBSERVATIONS rows must raise InsufficientDataError.
        This is the critical edge case: we must NEVER silently return a
        covariance matrix that is statistically meaningless.
        """
        rets = _synthetic_returns(n=MIN_OBSERVATIONS - 1)
        with pytest.raises(InsufficientDataError, match=str(MIN_OBSERVATIONS)):
            estimate_covariance(rets)

    def test_raises_at_exactly_boundary_minus_one(self):
        """n = 19 < 20 must still raise."""
        rets = _synthetic_returns(n=19)
        with pytest.raises(InsufficientDataError):
            estimate_covariance(rets)

    def test_succeeds_at_min_observations(self):
        """n = MIN_OBSERVATIONS = 20 must succeed."""
        rets = _synthetic_returns(n=MIN_OBSERVATIONS)
        result = estimate_covariance(rets)
        assert isinstance(result, CovarianceResult)

    def test_output_is_positive_semidefinite(self):
        """
        The Ledoit-Wolf covariance matrix must be positive-semidefinite.
        All eigenvalues must be ≥ -tolerance.
        Reference: PSD is a necessary property of any valid covariance matrix.
        """
        rets = _synthetic_returns(n=100, assets=5)
        result = estimate_covariance(rets)
        eigvals = np.linalg.eigvalsh(result.matrix)
        assert np.all(eigvals >= -1e-8), f"Non-PSD matrix: min eigval = {eigvals.min()}"

    def test_output_is_symmetric(self):
        """Covariance matrices must be exactly symmetric."""
        rets = _synthetic_returns(n=60, assets=4)
        result = estimate_covariance(rets)
        np.testing.assert_array_almost_equal(result.matrix, result.matrix.T)

    def test_diagonal_entries_are_non_negative(self):
        """Variances (diagonal entries) must be non-negative."""
        rets = _synthetic_returns(n=60, assets=4)
        result = estimate_covariance(rets)
        assert np.all(np.diag(result.matrix) >= 0)

    def test_shape_matches_assets(self):
        """Matrix shape must be (N, N) where N = number of asset columns."""
        n_assets = 6
        rets = _synthetic_returns(n=50, assets=n_assets)
        result = estimate_covariance(rets)
        assert result.matrix.shape == (n_assets, n_assets)

    def test_symbols_preserved_in_order(self):
        """Symbol list must match the DataFrame column order."""
        rets = _synthetic_returns(n=50, assets=3)
        result = estimate_covariance(rets)
        assert result.symbols == list(rets.columns)

    def test_n_obs_matches_clean_row_count(self):
        """n_obs should equal the number of complete rows (no NaN)."""
        rets = _synthetic_returns(n=60, assets=2)
        # Introduce one NaN row to verify it is dropped.
        rets.iloc[5, 0] = np.nan
        result = estimate_covariance(rets)
        assert result.n_obs == 59  # one row dropped

    def test_estimator_label_is_ledoit_wolf_on_normal_data(self):
        """On well-behaved data, the estimator should be 'ledoit_wolf'."""
        rets = _synthetic_returns(n=60, assets=3)
        result = estimate_covariance(rets)
        assert result.estimator == "ledoit_wolf"

    def test_single_asset_returns_1x1_matrix(self):
        """Single-asset portfolio: 1×1 covariance matrix = variance."""
        rets = _synthetic_returns(n=60, assets=1)
        result = estimate_covariance(rets)
        assert result.matrix.shape == (1, 1)
        # The single entry is the variance; must be positive.
        assert result.matrix[0, 0] > 0

    def test_nanrows_dropped_before_fitting(self):
        """Rows with any NaN must be excluded from the LW fit."""
        rets = _synthetic_returns(n=50, assets=2)
        # Set 5 rows to NaN in column 0.
        rets.iloc[:5, 0] = np.nan
        # Should succeed since 45 remaining rows ≥ 20.
        result = estimate_covariance(rets)
        assert result.n_obs == 45

    def test_fallback_to_diagonal_on_sklearn_failure(self, monkeypatch):
        """
        If sklearn's LedoitWolf.fit() raises, we must fall back to diagonal
        covariance — never propagate the exception to the caller.
        """
        rets = _synthetic_returns(n=60, assets=2)

        # Force sklearn to fail.
        from sklearn.covariance import LedoitWolf

        def bad_fit(self, X):
            raise RuntimeError("Simulated sklearn failure")

        monkeypatch.setattr(LedoitWolf, "fit", bad_fit)

        result = estimate_covariance(rets)
        # Must fall back gracefully, not raise.
        assert result.estimator == "diagonal_fallback"
        # Diagonal matrix: off-diagonals must be 0.
        cov = result.matrix
        np.testing.assert_array_almost_equal(
            cov - np.diag(np.diag(cov)), np.zeros_like(cov)
        )


# ── covariance_to_correlation ──────────────────────────────────────────────────


class TestCovarianceToCorrelation:
    def test_diagonal_is_exactly_one(self):
        """
        For any valid covariance matrix, the correlation matrix diagonal
        must be exactly 1.0.
        Reference: ρ_{ii} = σ_{ii} / (σ_i · σ_i) = 1.
        """
        rets = _synthetic_returns(n=100, assets=4)
        result = estimate_covariance(rets)
        corr = covariance_to_correlation(result.matrix)
        np.testing.assert_array_almost_equal(np.diag(corr), np.ones(4))

    def test_values_in_minus_one_to_one(self):
        """All correlation values must be in [-1, 1]."""
        rets = _synthetic_returns(n=100, assets=5)
        result = estimate_covariance(rets)
        corr = covariance_to_correlation(result.matrix)
        assert np.all(corr >= -1.0 - 1e-10)
        assert np.all(corr <= 1.0 + 1e-10)

    def test_symmetric(self):
        """Correlation matrix must be symmetric."""
        rets = _synthetic_returns(n=80, assets=4)
        result = estimate_covariance(rets)
        corr = covariance_to_correlation(result.matrix)
        np.testing.assert_array_almost_equal(corr, corr.T)

    def test_known_perfect_correlation(self):
        """
        Two perfectly correlated assets (one is a linear multiple of the other)
        should yield a correlation of exactly 1.0 (or as close as floating
        point allows). We test this with a known construction.
        """
        # Asset B = 2 * Asset A → perfect positive correlation.
        rng = np.random.default_rng(0)
        a = rng.normal(0, 0.01, 100)
        b = 2 * a
        df = pd.DataFrame({"A": a, "B": b})
        # Use a simple sample covariance since LW may shrink it slightly.
        cov = np.cov(df.to_numpy().T)
        corr = covariance_to_correlation(cov)
        # Off-diagonal should be very close to 1.0.
        np.testing.assert_allclose(corr[0, 1], 1.0, atol=1e-10)

    def test_zero_variance_asset_does_not_crash(self):
        """
        A zero-variance asset (constant price) must not cause division by zero.
        The resulting correlation for that asset is set to 0 for off-diagonal
        entries (the guard in covariance_to_correlation replaces std=0 with 1.0).
        """
        cov = np.array([[0.01, 0.0], [0.0, 0.0]])  # second asset zero variance
        # Must not raise.
        corr = covariance_to_correlation(cov)
        assert corr.shape == (2, 2)
        assert np.isfinite(corr).all()
