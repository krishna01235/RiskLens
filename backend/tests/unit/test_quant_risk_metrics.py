"""
tests/unit/test_quant_risk_metrics.py

Unit tests for quant/risk_metrics.py.

Tests use:
  - Synthetic normal returns with known analytical properties.
  - Exact textbook reference values where available.
  - Invariants (e.g. risk contributions sum to portfolio volatility).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.covariance import InsufficientDataError, estimate_covariance
from quant.risk_metrics import (
    MIN_OBSERVATIONS,
    compute_max_drawdown,
    compute_risk_contribution,
    compute_risk_estimate,
    compute_sharpe,
    compute_var_cvar,
    compute_volatility,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _normal_returns(n: int, mean: float = 0.0, std: float = 0.01, seed: int = 0):
    """Synthetic normal returns as a pd.Series."""
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mean, std, n), name="portfolio")


def _multi_returns(n: int, assets: int = 2, seed: int = 42) -> pd.DataFrame:
    """Multi-asset synthetic returns DataFrame."""
    rng = np.random.default_rng(seed)
    data = rng.normal(0.001, 0.02, size=(n, assets))
    return pd.DataFrame(data, columns=[f"A{i}" for i in range(assets)])


# ── compute_volatility ─────────────────────────────────────────────────────────


class TestComputeVolatility:
    def test_single_asset_equals_annualised_std(self):
        """
        For a single-asset portfolio with weight=1 and covariance=σ²,
        portfolio volatility = σ * sqrt(252).
        Reference: σ_p = sqrt(w^T Σ w) * sqrt(252) = σ * sqrt(252).
        """
        sigma_daily = 0.02
        cov = np.array([[sigma_daily**2]])
        weights = np.array([1.0])
        expected = sigma_daily * np.sqrt(252)
        result = compute_volatility(weights, cov)
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    def test_equal_weight_two_uncorrelated_assets(self):
        """
        Two uncorrelated assets, equal weight, same variance σ².
        Portfolio variance = 0.5² * σ² + 0.5² * σ² = 0.5 * σ².
        Portfolio vol = σ / sqrt(2) * sqrt(252).
        """
        sigma_daily = 0.02
        cov = np.diag([sigma_daily**2, sigma_daily**2])
        weights = np.array([0.5, 0.5])
        expected = (sigma_daily / np.sqrt(2)) * np.sqrt(252)
        result = compute_volatility(weights, cov)
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    def test_zero_variance_returns_zero(self):
        """Zero covariance (constant-price asset) must return 0, not error."""
        cov = np.zeros((2, 2))
        weights = np.array([0.5, 0.5])
        result = compute_volatility(weights, cov)
        assert result == 0.0

    def test_perfectly_correlated_two_assets(self):
        """
        Two perfectly correlated assets with equal weight and same σ²:
        portfolio vol = σ * sqrt(252)  (correlation=1 gives NO diversification).
        Reference: Var_p = (w_A σ + w_B σ)² = (0.5σ + 0.5σ)² = σ²
        """
        sigma_daily = 0.02
        cov = np.array(
            [
                [sigma_daily**2, sigma_daily**2],
                [sigma_daily**2, sigma_daily**2],
            ]
        )
        weights = np.array([0.5, 0.5])
        expected = sigma_daily * np.sqrt(252)
        result = compute_volatility(weights, cov)
        np.testing.assert_allclose(result, expected, rtol=1e-12)


# ── compute_var_cvar ───────────────────────────────────────────────────────────


class TestComputeVarCvar:
    def test_95_var_known_normal_approximation(self):
        """
        For N(0, σ) returns, VaR_95 ≈ 1.645 * σ.
        Using a large sample for convergence.
        """
        sigma = 0.02
        rng = np.random.default_rng(99)
        r = pd.Series(rng.normal(0, sigma, 100_000))
        var, _ = compute_var_cvar(r, confidence=0.95)
        # Within 5% of the theoretical value (Monte Carlo noise).
        np.testing.assert_allclose(var, 1.645 * sigma, rtol=0.05)

    def test_95_cvar_larger_than_var(self):
        """CVaR must always be ≥ VaR by definition (it's the tail mean)."""
        r = _normal_returns(500, std=0.02, seed=7)
        var, cvar = compute_var_cvar(r, confidence=0.95)
        assert cvar >= var, f"CVaR ({cvar}) must be ≥ VaR ({var})"

    def test_99_var_larger_than_95_var(self):
        """99% VaR must be larger (more conservative) than 95% VaR."""
        r = _normal_returns(500, std=0.02, seed=8)
        var_95, _ = compute_var_cvar(r, confidence=0.95)
        var_99, _ = compute_var_cvar(r, confidence=0.99)
        assert var_99 >= var_95

    def test_var_cvar_positive_on_zero_mean_normal(self):
        """VaR and CVaR should be positive (losses) for zero-mean returns."""
        r = _normal_returns(200, mean=0.0, std=0.02, seed=10)
        var, cvar = compute_var_cvar(r, confidence=0.95)
        assert var >= 0
        assert cvar >= 0

    def test_raises_on_insufficient_data(self):
        """Fewer than MIN_OBSERVATIONS must raise InsufficientDataError."""
        r = _normal_returns(MIN_OBSERVATIONS - 1)
        with pytest.raises(InsufficientDataError):
            compute_var_cvar(r)

    def test_constant_returns_var_negative_means_guaranteed_gain(self):
        """
        Constant positive returns → every observation = +0.001.
        VaR_95 = -percentile(r, 5%) = -0.001 (negative value = guaranteed gain).
        A negative VaR is mathematically correct: the portfolio cannot lose money
        over the historical window.  CVaR is also -0.001 (only one distinct value).
        Reference: VaR_α = -quantile(r, 1-α); if all returns > 0, VaR < 0.
        """
        r = pd.Series([0.001] * 50)
        var, cvar = compute_var_cvar(r, confidence=0.95)
        # Both must be exactly -0.001 (the 5th percentile of constant 0.001).
        np.testing.assert_allclose(var, -0.001, rtol=1e-10)
        np.testing.assert_allclose(cvar, -0.001, rtol=1e-10)

    def test_cvar_degenerate_empty_tail(self, monkeypatch):
        """
        In standard math, the 5th percentile is ≥ the minimum, so the tail is never
        empty. However, to test the safety guard `if len(tail) == 0: cvar = var`,
        we monkeypatch np.percentile to simulate a precision issue where the
        threshold falls strictly below the minimum element.
        """
        r = _normal_returns(50)
        # Mock np.percentile to return a value larger than -min(r) 
        # so that -var (which is the actual percentile) is < min(r).
        original_percentile = np.percentile
        
        def mock_percentile(a, q):
            return original_percentile(a, q) - 100.0  # artificially shift var so -var is way below min
    
        monkeypatch.setattr(np, "percentile", mock_percentile)
    
        var, cvar = compute_var_cvar(r, confidence=0.95)
        # The fallback should set cvar = var
        assert cvar == var

    def test_all_negative_returns_var_positive(self):
        """All-negative return series → VaR is a large positive loss."""
        r = pd.Series([-0.05] * 50)
        var, cvar = compute_var_cvar(r, confidence=0.95)
        assert var > 0
        np.testing.assert_allclose(var, 0.05, rtol=1e-6)


# ── compute_sharpe ─────────────────────────────────────────────────────────────


class TestComputeSharpe:
    def test_zero_mean_zero_rf_gives_zero_sharpe(self):
        """
        If mean return = 0 and risk-free = 0, Sharpe = 0.
        """
        rng = np.random.default_rng(99)
        # Exactly zero-mean returns (centre them).
        r = rng.normal(0, 0.02, 500)
        r -= r.mean()
        sharpe = compute_sharpe(pd.Series(r), risk_free_daily=0.0)
        np.testing.assert_allclose(sharpe, 0.0, atol=1e-6)

    def test_positive_return_positive_sharpe(self):
        """
        Strictly positive mean excess returns with non-zero std → positive Sharpe.
        Note: a *constant* return series has std=0 → the zero-std guard returns 0.0.
        We must use a series with positive mean AND non-zero variance.
        """
        rng = np.random.default_rng(42)
        # Force positive mean: shift above 0 after generation.
        noise = rng.normal(0, 0.01, 50)
        noise = noise - noise.mean() + 0.002  # shift mean to +0.002, keep variance
        r = pd.Series(noise)
        sharpe = compute_sharpe(r, risk_free_daily=0.0)
        assert sharpe > 0, f"Expected positive Sharpe, got {sharpe}"

    def test_sharpe_annualisation_factor(self):
        """
        For daily returns with mean=μ, std=σ, Sharpe = μ/σ * sqrt(252).
        Reference: S = (μ - r_f) / σ * sqrt(252).
        Use exact values to verify the sqrt(252) factor is applied.
        """
        mu = 0.001
        sigma = 0.01
        # Construct returns with exact mean and std.
        n = 100
        r = pd.Series([mu] * n)
        # std of a constant series is 0, so add small noise then adjust.
        # Instead, use a series where we know exact Sharpe.
        rng = np.random.default_rng(1)
        noise = rng.normal(0, sigma, n)
        noise = noise - noise.mean() + mu  # force exact mean
        r = pd.Series(noise)
        actual_std = float(r.std(ddof=1))
        expected = mu / actual_std * np.sqrt(252)
        result = compute_sharpe(r, risk_free_daily=0.0)
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_raises_on_insufficient_data(self):
        r = _normal_returns(MIN_OBSERVATIONS - 1)
        with pytest.raises(InsufficientDataError):
            compute_sharpe(r)

    def test_constant_returns_std_zero_returns_zero(self):
        """Constant return series → std = 0 → Sharpe = 0 (guard, no ZeroDivision)."""
        r = pd.Series([0.001] * 50)
        sharpe = compute_sharpe(r)
        assert sharpe == 0.0


# ── compute_max_drawdown ───────────────────────────────────────────────────────


class TestComputeMaxDrawdown:
    def test_monotonically_increasing_returns_zero_drawdown(self):
        """Strictly positive returns → cumulative return never falls → MDD = 0."""
        r = pd.Series([0.01] * 50)
        assert compute_max_drawdown(r) == pytest.approx(0.0, abs=1e-10)

    def test_known_drawdown_sequence(self):
        """
        Construct a return series with a known drawdown.
        Prices: [1, 1.1, 0.99, 0.99, 1.05].
        Returns (simple): [0.1, -0.1/1.1, 0, 1.05/0.99-1].
        Cumulative: [1, 1.1, 0.99, 0.99, 1.05].
        Peak at index 1: 1.1.
        Max drawdown = (1.1 - 0.99) / 1.1 = 0.11/1.1 = 0.1.
        """
        # Use cumulative products matching the price series [1, 1.1, 0.99, 0.99, 1.05].
        simple_returns = pd.Series(
            [
                0.10,  # 1 → 1.1
                -0.11 / 1.1,  # 1.1 → 0.99
                0.0,  # 0.99 → 0.99
                1.05 / 0.99 - 1,  # 0.99 → 1.05
            ]
            + [0.01] * (MIN_OBSERVATIONS - 4)  # pad to meet MIN_OBSERVATIONS
        )
        mdd = compute_max_drawdown(simple_returns)
        # Expected MDD from peak=1.1, trough=0.99.
        expected = (1.1 - 0.99) / 1.1
        np.testing.assert_allclose(mdd, expected, rtol=1e-6)

    def test_all_negative_returns_large_drawdown(self):
        """All-negative return series → large positive drawdown fraction."""
        r = pd.Series([-0.01] * 50)
        mdd = compute_max_drawdown(r)
        assert mdd > 0

    def test_raises_on_insufficient_data(self):
        r = _normal_returns(MIN_OBSERVATIONS - 1)
        with pytest.raises(InsufficientDataError):
            compute_max_drawdown(r)

    def test_mdd_is_non_negative(self):
        """Max drawdown must always be non-negative."""
        rng = np.random.default_rng(5)
        r = pd.Series(rng.normal(0.001, 0.02, 200))
        mdd = compute_max_drawdown(r)
        assert mdd >= 0


# ── compute_risk_contribution ──────────────────────────────────────────────────


class TestComputeRiskContribution:
    def _get_equal_weight_uncorrelated(self, n_assets: int = 2, sigma: float = 0.02):
        """
        Equal-weight, diagonal (uncorrelated) covariance.
        Portfolio vol = sigma * sqrt(1/n_assets).
        Each RC = sigma² / n_assets / sigma_p (same for all assets).
        """
        w = np.ones(n_assets) / n_assets
        cov = np.diag([sigma**2] * n_assets)
        symbols = [f"A{i}" for i in range(n_assets)]
        return w, cov, symbols

    def test_risk_contributions_sum_to_portfolio_volatility(self):
        """
        Critical invariant: sum(RC_i) = σ_p (daily, NOT annualised).
        Reference: Euler's theorem for homogeneous functions of degree 1.
        """
        rets = _multi_returns(100, assets=4)
        cov_result = estimate_covariance(rets)
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        symbols = cov_result.symbols

        rcs = compute_risk_contribution(weights, cov_result.matrix, symbols)
        sigma_p = np.sqrt(weights @ cov_result.matrix @ weights)

        rc_sum = sum(rc.rc for rc in rcs)
        np.testing.assert_allclose(rc_sum, sigma_p, rtol=1e-10)

    def test_rc_pct_sum_to_one(self):
        """rc_pct values must sum to 1.0 (they are fractions of total vol)."""
        rets = _multi_returns(100, assets=3)
        cov_result = estimate_covariance(rets)
        weights = np.ones(3) / 3
        rcs = compute_risk_contribution(weights, cov_result.matrix, cov_result.symbols)
        np.testing.assert_allclose(sum(rc.rc_pct for rc in rcs), 1.0, rtol=1e-10)

    def test_equal_weight_uncorrelated_equal_rc(self):
        """
        Equal weights + uncorrelated, equal-variance assets → equal RC.
        Each asset contributes equally to portfolio risk.
        """
        w, cov, symbols = self._get_equal_weight_uncorrelated(n_assets=3)
        rcs = compute_risk_contribution(w, cov, symbols)
        rc_vals = [rc.rc_pct for rc in rcs]
        # All should be equal (1/3 each).
        np.testing.assert_allclose(rc_vals, [1 / 3] * 3, rtol=1e-10)

    def test_raises_on_mismatched_lengths(self):
        """len(weights) must match len(symbols)."""
        w = np.array([0.5, 0.5])
        cov = np.diag([0.01, 0.01])
        with pytest.raises(ValueError, match="must equal"):
            compute_risk_contribution(w, cov, ["A"])

    def test_raises_on_zero_portfolio_volatility(self):
        """Zero covariance matrix → portfolio vol = 0 → undefined RC."""
        w = np.array([0.5, 0.5])
        cov = np.zeros((2, 2))
        with pytest.raises(ValueError, match="zero"):
            compute_risk_contribution(w, cov, ["A", "B"])

    def test_single_asset_full_rc(self):
        """Single-asset portfolio: that asset has 100% risk contribution."""
        w = np.array([1.0])
        cov = np.array([[0.02**2]])
        rcs = compute_risk_contribution(w, cov, ["A"])
        assert len(rcs) == 1
        np.testing.assert_allclose(rcs[0].rc_pct, 1.0, rtol=1e-10)

    def test_larger_weight_asset_higher_rc_in_correlated_portfolio(self):
        """
        In a 2-asset portfolio with 80/20 weights and equal, uncorrelated variance,
        the 80% asset must have a higher risk contribution than the 20% one.
        RC_i = w_i² * σ² / σ_p; since σ² and σ_p are the same for both,
        the 80% asset has 4× the risk contribution of the 20% asset.
        """
        sigma = 0.02
        w = np.array([0.8, 0.2])
        cov = np.diag([sigma**2, sigma**2])
        rcs = compute_risk_contribution(w, cov, ["A", "B"])
        assert rcs[0].rc > rcs[1].rc


# ── compute_risk_estimate (integration of all metrics) ────────────────────────


class TestComputeRiskEstimate:
    def test_insufficient_data_flag(self):
        """
        With fewer than MIN_OBSERVATIONS portfolio return observations,
        compute_risk_estimate must return insufficient_data=True
        and must NOT raise — it surfaces an explicit state instead.
        """
        r = _normal_returns(MIN_OBSERVATIONS - 1)
        cov = np.diag([0.0004])
        w = np.array([1.0])
        result = compute_risk_estimate(r, w, cov, ["A"])
        assert result.insufficient_data is True
        assert result.volatility == 0.0
        assert result.var_95 == 0.0
        assert result.cvar_95 == 0.0
        assert result.sharpe is None

    def test_full_estimate_on_sufficient_data(self):
        """
        With sufficient data, all fields must be populated and sane:
          - volatility > 0
          - cvar_95 >= var_95 >= 0
          - max_drawdown >= 0
          - risk_contributions is non-empty
          - insufficient_data is False
        """
        rets = _multi_returns(150, assets=3)
        from quant.covariance import estimate_covariance
        from quant.returns import compute_weights

        holdings = {"A0": (1.0, 100.0), "A1": (2.0, 50.0), "A2": (1.0, 200.0)}
        weight_dict = compute_weights(holdings)
        w = np.array([weight_dict["A0"], weight_dict["A1"], weight_dict["A2"]])

        cov_result = estimate_covariance(rets)
        portfolio_rets = (rets * w).sum(axis=1)

        result = compute_risk_estimate(
            portfolio_rets, w, cov_result.matrix, cov_result.symbols
        )

        assert not result.insufficient_data
        assert result.volatility > 0
        assert result.var_95 >= 0
        assert result.cvar_95 >= result.var_95
        assert result.max_drawdown >= 0
        assert len(result.risk_contributions) == 3
        assert result.n_obs == len(portfolio_rets)

    def test_risk_contributions_sum_invariant_in_full_estimate(self):
        """
        RC sum invariant must hold even when called through compute_risk_estimate.
        """
        rets = _multi_returns(120, assets=2)
        from quant.covariance import estimate_covariance

        cov_result = estimate_covariance(rets)
        w = np.array([0.6, 0.4])
        portfolio_rets = (rets * w).sum(axis=1)

        result = compute_risk_estimate(
            portfolio_rets, w, cov_result.matrix, cov_result.symbols
        )

        if not result.insufficient_data and result.risk_contributions:
            sigma_p_daily = np.sqrt(w @ cov_result.matrix @ w)
            rc_sum = sum(rc.rc for rc in result.risk_contributions)
            np.testing.assert_allclose(rc_sum, sigma_p_daily, rtol=1e-9)

    def test_full_estimate_zero_volatility_rc_fallback(self):
        """
        If the portfolio volatility is exactly zero, compute_risk_contribution
        raises ValueError. compute_risk_estimate should catch this and
        set risk_contributions = [].
        """
        r = _normal_returns(50)
        w = np.array([0.5, 0.5])
        cov = np.zeros((2, 2))  # Zero volatility matrix
        
        result = compute_risk_estimate(r, w, cov, ["A", "B"])
        # Should not raise, RC list should be empty
        assert not result.insufficient_data
        assert result.volatility == 0.0
        assert result.risk_contributions == []

class TestCorrelationClusters:
    def test_cov_to_corr(self):
        from quant.risk_metrics import cov_to_corr
        
        # Diagonal is 4, so std is 2.
        # cov(0, 1) = 2, so corr(0, 1) = 2 / (2 * 2) = 0.5
        cov_matrix = np.array([
            [4.0, 2.0],
            [2.0, 4.0]
        ])
        
        corr = cov_to_corr(cov_matrix)
        
        np.testing.assert_allclose(corr, np.array([
            [1.0, 0.5],
            [0.5, 1.0]
        ]))

    def test_cov_to_corr_zero_variance(self):
        from quant.risk_metrics import cov_to_corr
        
        cov_matrix = np.array([
            [4.0, 0.0],
            [0.0, 0.0]
        ])
        
        corr = cov_to_corr(cov_matrix)
        
        # Zero variance asset should have 0 correlation with others, 1.0 with itself
        np.testing.assert_allclose(corr, np.array([
            [1.0, 0.0],
            [0.0, 1.0]
        ]))

    def test_detect_correlation_clusters_synthetic(self):
        from quant.risk_metrics import detect_correlation_clusters
        
        symbols = ["AAPL", "MSFT", "GOOG", "JPM", "BAC", "GOLD"]
        
        # Synthetic correlation matrix
        # AAPL, MSFT, GOOG are highly correlated (>0.7)
        # JPM, BAC are highly correlated (>0.7)
        # GOLD is uncorrelated
        
        corr = np.array([
            [1.0, 0.8, 0.9, 0.1, 0.1, -0.1],  # AAPL
            [0.8, 1.0, 0.75, 0.2, 0.1, -0.2], # MSFT
            [0.9, 0.75, 1.0, 0.0, 0.1, -0.1], # GOOG
            [0.1, 0.2, 0.0, 1.0, 0.85, 0.0],  # JPM
            [0.1, 0.1, 0.1, 0.85, 1.0, 0.1],  # BAC
            [-0.1, -0.2, -0.1, 0.0, 0.1, 1.0] # GOLD
        ])
        
        clusters = detect_correlation_clusters(corr, symbols, threshold=0.7)
        
        clusters_as_sets = [set(c) for c in clusters]
        
        assert len(clusters) == 2
        assert {"AAPL", "GOOG", "MSFT"} in clusters_as_sets
        assert {"BAC", "JPM"} in clusters_as_sets
        
    def test_detect_correlation_clusters_empty(self):
        from quant.risk_metrics import detect_correlation_clusters
        
        symbols = ["A", "B", "C"]
        corr = np.eye(3) # Identity matrix -> zero off-diagonal correlations
        
        clusters = detect_correlation_clusters(corr, symbols, threshold=0.7)
        assert len(clusters) == 0  # No single-item clusters
        
    def test_detect_correlation_clusters_one_asset(self):
        from quant.risk_metrics import detect_correlation_clusters
        
        symbols = ["A"]
        corr = np.array([[1.0]])
        
        clusters = detect_correlation_clusters(corr, symbols, threshold=0.7)
        assert len(clusters) == 0

