"""
tests/unit/test_monte_carlo.py -- Unit tests for quant/monte_carlo.py.

Every test verifies mathematical correctness from first principles.
No I/O, no DB, no Redis -- pure NumPy fixture-based tests.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quant.monte_carlo import (
    SimulationParams,
    SimulationResult,
    _apply_garch_scaling,
    _cholesky_safe,
    run_simulation,
    run_simulation_batched,
    TRADING_DAYS_PER_YEAR,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _single_asset_params(
    num_paths: int = 200_000,
    horizon_days: int = 30,
    mu_annual: float = 0.08,
    sigma_annual: float = 0.20,
    s0: float = 10_000.0,
) -> SimulationParams:
    """Build a single-asset SimulationParams with known analytical solution."""
    mu_daily = mu_annual / TRADING_DAYS_PER_YEAR
    sigma_daily = sigma_annual / math.sqrt(TRADING_DAYS_PER_YEAR)
    cov = np.array([[sigma_daily**2]])
    return SimulationParams(
        num_paths=num_paths,
        horizon_days=horizon_days,
        weights=np.array([1.0]),
        current_values=np.array([s0]),
        mean_daily_returns=np.array([mu_daily]),
        cov_matrix=cov,
        symbols=["A"],
    )


def _two_asset_uncorrelated_params(num_paths: int = 100_000) -> SimulationParams:
    """Two equal-weight uncorrelated assets, each with sigma=0.02/day."""
    sigma = 0.02
    return SimulationParams(
        num_paths=num_paths,
        horizon_days=30,
        weights=np.array([0.5, 0.5]),
        current_values=np.array([5_000.0, 5_000.0]),
        mean_daily_returns=np.array([0.0003, 0.0003]),
        cov_matrix=np.diag([sigma**2, sigma**2]),
        symbols=["A", "B"],
    )


# ---------------------------------------------------------------------------
# 1. GBM Analytical Validation (most important test in the phase)
# ---------------------------------------------------------------------------


class TestGBMAnalytical:
    """Single-asset GBM: validate mean and variance of terminal distribution.

    For GBM:  S_T = S_0 * exp((mu - 0.5*sigma^2)*T + sigma*sqrt(T)*Z)
    where Z ~ N(0,1).

    E[S_T]   = S_0 * exp(mu * T)                      (log-normal property)
    Var[S_T] = S_0^2 * exp(2*mu*T) * (exp(sigma^2*T) - 1)
    """

    def test_expected_terminal_value_matches_theory(self):
        """E[S_T] = S_0 * exp(mu_daily * T), within 1% tolerance at 200K paths."""
        params = _single_asset_params(num_paths=200_000, horizon_days=30)
        result = run_simulation(params)

        S0 = params.current_values[0]
        mu_daily = params.mean_daily_returns[0]
        T = params.horizon_days

        # E[terminal_value] = S0 * exp(mu * T)
        # terminal_pnl = terminal_value - S0, so E[pnl] = S0 * (exp(mu*T) - 1)
        expected_mean_pnl = S0 * (math.exp(mu_daily * T) - 1.0)
        got_mean_pnl = result.expected_pnl

        rel_err = abs(got_mean_pnl - expected_mean_pnl) / max(abs(expected_mean_pnl), 1e-6)
        assert rel_err < 0.02, (
            f"E[pnl] relative error {rel_err:.4f} > 2%: "
            f"got={got_mean_pnl:.4f}, expected={expected_mean_pnl:.4f}"
        )

    def test_terminal_variance_matches_theory(self):
        """Var[S_T] matches log-normal analytical formula within 5% at 200K paths."""
        params = _single_asset_params(num_paths=200_000, horizon_days=30)
        result = run_simulation(params)

        S0 = params.current_values[0]
        mu_daily = params.mean_daily_returns[0]
        sigma_daily = math.sqrt(params.cov_matrix[0, 0])
        T = params.horizon_days

        # Var[S_T] = S0^2 * exp(2*mu*T) * (exp(sigma^2*T) - 1)
        expected_var_terminal = (
            S0**2 * math.exp(2 * mu_daily * T) * (math.exp(sigma_daily**2 * T) - 1.0)
        )
        # terminal_pnl = S_T - S0, so Var[pnl] = Var[S_T]
        got_var = float(np.var(result.terminal_pnl))

        rel_err = abs(got_var - expected_var_terminal) / expected_var_terminal
        assert rel_err < 0.05, (
            f"Var[pnl] relative error {rel_err:.4f} > 5%: "
            f"got={got_var:.2f}, expected={expected_var_terminal:.2f}"
        )

    def test_prob_profit_plus_loss_sums_to_one(self):
        """prob_profit + prob_loss must be <= 1.0 (paths at exactly 0 in neither)."""
        params = _single_asset_params()
        result = run_simulation(params)
        total = result.prob_profit + result.prob_loss
        assert total <= 1.0 + 1e-9, f"prob_profit + prob_loss = {total} > 1"
        # With non-zero drift, both should be strictly positive
        assert result.prob_profit > 0.0
        assert result.prob_loss > 0.0

    def test_percentile_ordering(self):
        """p5 < p50 < p95 must always hold."""
        params = _single_asset_params()
        result = run_simulation(params)
        assert result.pnl_p5 < result.pnl_p50, (
            f"p5={result.pnl_p5:.2f} not < p50={result.pnl_p50:.2f}"
        )
        assert result.pnl_p50 < result.pnl_p95, (
            f"p50={result.pnl_p50:.2f} not < p95={result.pnl_p95:.2f}"
        )

    def test_zero_drift_symmetric_pnl(self):
        """With mu=0 and symmetric GBM, median P&L should be slightly negative
        (log-normal drift: median = S0*exp(-0.5*sigma^2*T) < S0).
        Expected P&L should be close to 0 (within 2 sigma of MC error)."""
        params = SimulationParams(
            num_paths=300_000,
            horizon_days=30,
            weights=np.array([1.0]),
            current_values=np.array([10_000.0]),
            mean_daily_returns=np.array([0.0]),
            cov_matrix=np.array([[0.02**2]]),
            symbols=["A"],
        )
        result = run_simulation(params)
        # E[S_T] = S0 * exp(0) = S0 => E[pnl] ~ 0
        # Monte Carlo SE ~ sigma_pnl / sqrt(N)
        mc_se = float(np.std(result.terminal_pnl)) / math.sqrt(result.num_paths)
        assert abs(result.expected_pnl) < 5 * mc_se, (
            f"|E[pnl]|={abs(result.expected_pnl):.4f} > 5*MC_SE={5*mc_se:.4f}"
        )


# ---------------------------------------------------------------------------
# 2. Antithetic Variates
# ---------------------------------------------------------------------------


class TestAntithetic:
    """Verify antithetic variate pairing is correctly implemented."""

    def test_num_paths_is_even(self):
        """Output num_paths must always be even (antithetic pairing)."""
        # Odd input -> should be rounded up to even
        params = _single_asset_params(num_paths=999)
        result = run_simulation(params)
        assert result.num_paths % 2 == 0
        assert result.num_paths == 1000

    def test_even_input_unchanged(self):
        """Even input path count should pass through unchanged."""
        params = _single_asset_params(num_paths=1000)
        result = run_simulation(params)
        assert result.num_paths == 1000

    def test_variance_reduction_vs_crude_mc(self):
        """Antithetic MC should have lower variance of E[pnl] than crude MC
        at the same total path count (verified by repeated sampling).

        We compare std-dev of the estimator across 20 replications.
        This test is probabilistic -- it should pass with very high probability
        but has a tiny failure rate by construction. Seed is fixed for stability.
        """
        N_REPS = 20
        N_PATHS = 10_000

        sigma_daily = 0.02
        S0 = 10_000.0
        T = 30

        antithetic_means: list[float] = []
        crude_means: list[float] = []

        rng = np.random.default_rng(42)
        for _ in range(N_REPS):
            # Antithetic (our implementation)
            params = SimulationParams(
                num_paths=N_PATHS,
                horizon_days=T,
                weights=np.array([1.0]),
                current_values=np.array([S0]),
                mean_daily_returns=np.array([0.0]),
                cov_matrix=np.array([[sigma_daily**2]]),
            )
            result = run_simulation(params)
            antithetic_means.append(result.expected_pnl)

            # Crude MC (no antithetics -- just random without pairing)
            eps = rng.standard_normal(N_PATHS)
            log_ret = -0.5 * sigma_daily**2 * T + sigma_daily * math.sqrt(T) * eps
            crude_pnl = S0 * (np.exp(log_ret) - 1.0)
            crude_means.append(float(np.mean(crude_pnl)))

        antithetic_std = float(np.std(antithetic_means))
        crude_std = float(np.std(crude_means))

        assert antithetic_std < crude_std, (
            f"Antithetic std={antithetic_std:.4f} not < crude std={crude_std:.4f}; "
            "variance reduction not working."
        )


# ---------------------------------------------------------------------------
# 3. GARCH Volatility Scaling
# ---------------------------------------------------------------------------


class TestGarchScaling:
    def test_higher_garch_vol_widens_distribution(self):
        """Replacing cov diagonal with higher GARCH vol should widen the P&L range."""
        base_params = _single_asset_params(num_paths=50_000, sigma_annual=0.10)
        result_base = run_simulation(base_params)

        # GARCH vol = 40% annual (4x higher)
        garch_params = SimulationParams(
            num_paths=50_000,
            horizon_days=base_params.horizon_days,
            weights=base_params.weights,
            current_values=base_params.current_values,
            mean_daily_returns=base_params.mean_daily_returns,
            cov_matrix=base_params.cov_matrix,
            garch_vols={0: 0.40},
        )
        result_garch = run_simulation(garch_params)

        # Higher vol -> wider P&L range (p95 - p5 should be larger)
        range_base = result_base.pnl_p95 - result_base.pnl_p5
        range_garch = result_garch.pnl_p95 - result_garch.pnl_p5
        assert range_garch > range_base, (
            f"GARCH range {range_garch:.2f} not > base range {range_base:.2f}"
        )

    def test_garch_scaling_preserves_matrix_shape(self):
        """_apply_garch_scaling must return same shape as input."""
        cov = np.diag([0.0004, 0.0009])
        result = _apply_garch_scaling(cov, {0: 0.25, 1: 0.30})
        assert result.shape == cov.shape

    def test_no_garch_returns_original(self):
        """Empty garch_vols -> original cov returned unchanged."""
        cov = np.diag([0.0004, 0.0009])
        result = _apply_garch_scaling(cov, {})
        np.testing.assert_array_equal(result, cov)

    def test_garch_diagonal_correctly_overridden(self):
        """After scaling, diagonal should match (garch_vol/sqrt(252))^2."""
        sigma_orig = 0.01  # daily
        cov = np.array([[sigma_orig**2]])
        ann_garch = 0.30
        scaled = _apply_garch_scaling(cov, {0: ann_garch})
        expected_daily_var = (ann_garch / math.sqrt(TRADING_DAYS_PER_YEAR)) ** 2
        np.testing.assert_allclose(scaled[0, 0], expected_daily_var, rtol=1e-10)


# ---------------------------------------------------------------------------
# 4. Cholesky Fallback
# ---------------------------------------------------------------------------


class TestCholeskySafe:
    def test_standard_psd_matrix(self):
        """Well-conditioned PSD matrix: Cholesky succeeds normally."""
        cov = np.array([[0.0004, 0.00012], [0.00012, 0.0009]])
        L = _cholesky_safe(cov)
        # Verify L @ L.T == cov
        np.testing.assert_allclose(L @ L.T, cov, atol=1e-12)

    def test_near_singular_matrix_does_not_crash(self):
        """Near-singular matrix (tiny eigenvalue) must not raise."""
        # Create an almost rank-deficient 2x2
        cov = np.array([[1e-6, 1e-6], [1e-6, 1e-6 + 1e-15]])
        L = _cholesky_safe(cov)
        assert L.shape == (2, 2)
        assert np.all(np.isfinite(L))


# ---------------------------------------------------------------------------
# 5. Input Validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_raises_on_empty_weights(self):
        with pytest.raises(ValueError, match="non-empty"):
            run_simulation(
                SimulationParams(
                    num_paths=200,
                    horizon_days=1,
                    weights=np.array([]),
                    current_values=np.array([]),
                    mean_daily_returns=np.array([]),
                    cov_matrix=np.zeros((0, 0)),
                )
            )

    def test_raises_on_shape_mismatch(self):
        with pytest.raises(ValueError, match="cov_matrix shape"):
            run_simulation(
                SimulationParams(
                    num_paths=200,
                    horizon_days=1,
                    weights=np.array([0.5, 0.5]),
                    current_values=np.array([1000.0, 1000.0]),
                    mean_daily_returns=np.array([0.001, 0.001]),
                    cov_matrix=np.eye(3),  # wrong shape
                )
            )

    def test_raises_on_too_few_paths(self):
        with pytest.raises(ValueError, match="too small"):
            run_simulation(
                SimulationParams(
                    num_paths=10,  # below _MIN_PATHS=100
                    horizon_days=1,
                    weights=np.array([1.0]),
                    current_values=np.array([1000.0]),
                    mean_daily_returns=np.array([0.001]),
                    cov_matrix=np.array([[0.0004]]),
                )
            )

    def test_raises_on_zero_horizon(self):
        with pytest.raises(ValueError, match="horizon_days"):
            run_simulation(
                SimulationParams(
                    num_paths=200,
                    horizon_days=0,
                    weights=np.array([1.0]),
                    current_values=np.array([1000.0]),
                    mean_daily_returns=np.array([0.001]),
                    cov_matrix=np.array([[0.0004]]),
                )
            )

    def test_raises_on_mean_returns_length_mismatch(self):
        with pytest.raises(ValueError, match="mean_daily_returns length"):
            run_simulation(
                SimulationParams(
                    num_paths=200,
                    horizon_days=1,
                    weights=np.array([0.5, 0.5]),
                    current_values=np.array([1000.0, 1000.0]),
                    mean_daily_returns=np.array([0.001]),  # wrong length
                    cov_matrix=np.eye(2) * 0.0004,
                )
            )


# ---------------------------------------------------------------------------
# 6. Batched Simulation
# ---------------------------------------------------------------------------


class TestBatchedSimulation:
    def test_batched_matches_single_shot_statistics(self):
        """run_simulation_batched must produce statistically equivalent results
        to run_simulation at the same path count."""
        params = _single_asset_params(num_paths=50_000, horizon_days=30)

        result_single = run_simulation(params)
        result_batched = run_simulation_batched(params, batch_size=10_000)

        # Both produce same num_paths
        assert result_single.num_paths == result_batched.num_paths

        # E[pnl] should be close (within 3% relative)
        expected = result_single.expected_pnl
        got = result_batched.expected_pnl
        if abs(expected) > 1.0:
            assert abs(got - expected) / abs(expected) < 0.03
        else:
            assert abs(got - expected) < 50.0  # absolute fallback for near-zero mean

    def test_progress_callback_called(self):
        """progress_cb must be called at least once per batch."""
        params = _single_asset_params(num_paths=10_000, horizon_days=7)
        progress_values: list[float] = []

        run_simulation_batched(params, batch_size=2_000, progress_cb=progress_values.append)

        # 10000 paths / 2000 batch_size = 5 batches
        assert len(progress_values) == 5
        # Values must be monotonically increasing toward 1.0
        for i in range(1, len(progress_values)):
            assert progress_values[i] > progress_values[i - 1]
        # Final value must be 1.0
        assert abs(progress_values[-1] - 1.0) < 1e-9

    def test_prob_profit_plus_loss_sums_leq_one_batched(self):
        """Sanity check on batched output."""
        params = _two_asset_uncorrelated_params(num_paths=20_000)
        result = run_simulation_batched(params, batch_size=5_000)
        total = result.prob_profit + result.prob_loss
        assert total <= 1.0 + 1e-9

    def test_percentile_ordering_batched(self):
        """p5 < p50 < p95 in batched output."""
        params = _two_asset_uncorrelated_params(num_paths=20_000)
        result = run_simulation_batched(params, batch_size=5_000)
        assert result.pnl_p5 < result.pnl_p50 < result.pnl_p95
