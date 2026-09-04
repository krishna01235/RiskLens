"""tests/unit/test_scenarios.py — Deterministic scenario evaluator tests.

All tests are purely numerical; no LLM, no database, no Redis.
Each test validates against analytically-computable reference values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.scenarios import ScenarioResult, evaluate_scenario


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_returns(seed: int = 42, n: int = 100) -> pd.DataFrame:
    """Synthetic 2-asset log-return DataFrame with known properties."""
    rng = np.random.default_rng(seed)
    # AAPL: low vol, NVDA: high vol
    aapl_r = rng.normal(0.001, 0.010, n)
    nvda_r = rng.normal(0.001, 0.030, n)
    return pd.DataFrame({"AAPL": aapl_r, "NVDA": nvda_r})


_WEIGHTS_2 = {"AAPL": 0.6, "NVDA": 0.4}
_PORTFOLIO_VALUE = 100_000.0


# ---------------------------------------------------------------------------
# Test 1 — High-vol shock: shock to the high-vol asset increases CVaR
# ---------------------------------------------------------------------------

class TestEvaluateScenario:
    def test_increasing_high_vol_weight_increases_cvar(self) -> None:
        """Increase the weight of the high-volatility asset and CVaR must rise.

        We shock AAPL (low-vol) down and NVDA (high-vol) up, so the portfolio
        becomes more concentrated in the high-vol asset.
        """
        returns = _make_returns()
        # Shock: AAPL -40%, NVDA +0% -> portfolio tilts heavily toward NVDA
        result_tilted = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"AAPL": -0.80},  # drastically reduce low-vol position
            portfolio_value=_PORTFOLIO_VALUE,
        )
        result_baseline = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"AAPL": 0.0},   # no-op shock for baseline
            portfolio_value=_PORTFOLIO_VALUE,
        )
        # Tilting toward the high-vol asset must increase CVaR.
        assert result_tilted.cvar_95 > result_baseline.cvar_95, (
            f"Tilted CVaR {result_tilted.cvar_95:.4f} should exceed baseline "
            f"{result_baseline.cvar_95:.4f}"
        )

    def test_expected_loss_sign_convention(self) -> None:
        """A negative shock produces a positive expected_loss (loss expressed as positive)."""
        returns = _make_returns()
        result = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"NVDA": -0.20},
            portfolio_value=_PORTFOLIO_VALUE,
        )
        # expected_loss = -(w_NVDA * portfolio_value * shock) = -(0.4 * 100_000 * -0.20) = +8_000
        expected_analytical = 0.4 * _PORTFOLIO_VALUE * 0.20  # 8_000
        assert result.expected_loss > 0, "Expected loss must be positive for a negative shock"
        assert abs(result.expected_loss - expected_analytical) < 1.0, (
            f"Expected ~{expected_analytical:.0f}, got {result.expected_loss:.0f}"
        )

    def test_zero_shocks_returns_unchanged_metrics(self) -> None:
        """All-zero shocks produce metrics identical to baseline within tolerance."""
        returns = _make_returns()
        result = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"NVDA": 0.0},
            portfolio_value=_PORTFOLIO_VALUE,
        )
        assert abs(result.var_95 - result.var_95_baseline) < 1e-10
        assert abs(result.cvar_95 - result.cvar_95_baseline) < 1e-10
        assert abs(result.expected_loss) < 1e-10

    def test_positive_shock_reduces_loss(self) -> None:
        """A +30% shock to all assets reduces expected_loss (gain scenario)."""
        returns = _make_returns()
        result = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"AAPL": 0.30, "NVDA": 0.30},
            portfolio_value=_PORTFOLIO_VALUE,
        )
        # expected_loss should be negative (a gain)
        assert result.expected_loss < 0

    # -----------------------------------------------------------------------
    # Test 2 — Unknown symbol raises ValueError
    # -----------------------------------------------------------------------

    def test_unknown_symbol_raises_value_error(self) -> None:
        """A shock for a symbol not in the portfolio must raise ValueError."""
        returns = _make_returns()
        with pytest.raises(ValueError, match="is not in the portfolio"):
            evaluate_scenario(
                weights=_WEIGHTS_2,
                returns_df=returns,
                shocks={"TSLA": -0.15},
            )

    def test_shock_exactly_minus_one_raises_value_error(self) -> None:
        """A shock of exactly -1.0 is disallowed (liquidates the position)."""
        returns = _make_returns()
        with pytest.raises(ValueError, match="out of the allowed range"):
            evaluate_scenario(
                weights=_WEIGHTS_2,
                returns_df=returns,
                shocks={"NVDA": -1.0},
            )

    def test_shock_out_of_range_positive(self) -> None:
        """A shock >= 1.0 is disallowed."""
        returns = _make_returns()
        with pytest.raises(ValueError, match="out of the allowed range"):
            evaluate_scenario(
                weights=_WEIGHTS_2,
                returns_df=returns,
                shocks={"NVDA": 1.5},
            )

    # -----------------------------------------------------------------------
    # Test 3 — Insufficient data sets the flag
    # -----------------------------------------------------------------------

    def test_insufficient_data_flag(self) -> None:
        """Fewer than MIN_OBSERVATIONS rows sets insufficient_data=True."""
        short_returns = _make_returns(n=10)  # 10 rows < MIN_OBSERVATIONS=20
        result = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=short_returns,
            shocks={"NVDA": -0.10},
        )
        assert result.insufficient_data is True

    def test_sufficient_data_flag(self) -> None:
        """100 rows is above MIN_OBSERVATIONS — flag must be False."""
        returns = _make_returns(n=100)
        result = evaluate_scenario(
            weights=_WEIGHTS_2,
            returns_df=returns,
            shocks={"NVDA": -0.10},
        )
        assert result.insufficient_data is False

    # -----------------------------------------------------------------------
    # Test 4 — Single-asset portfolio (degenerate case)
    # -----------------------------------------------------------------------

    def test_single_asset_portfolio(self) -> None:
        """A single-asset portfolio does not raise; metrics are defined."""
        returns = pd.DataFrame({"AAPL": np.random.default_rng(0).normal(0, 0.015, 100)})
        result = evaluate_scenario(
            weights={"AAPL": 1.0},
            returns_df=returns,
            shocks={"AAPL": -0.20},
            portfolio_value=50_000.0,
        )
        assert result.cvar_95 > 0
        # Expected loss: 1.0 * 50_000 * 0.20 = 10_000
        assert abs(result.expected_loss - 10_000.0) < 1.0

    # -----------------------------------------------------------------------
    # Test 5 — Analytical CVaR reference for a known distribution
    # -----------------------------------------------------------------------

    def test_analytical_var_reference(self) -> None:
        """With a known normal distribution, VaR is close to the analytical value.

        For an equal-weight portfolio of two uncorrelated N(0, sigma) assets:
            portfolio sigma = sigma / sqrt(2)
            95% historical VaR ~= 1.645 * (sigma / sqrt(2))

        We allow 25% tolerance given finite samples (n=1000).
        """
        sigma = 0.01
        rng = np.random.default_rng(7)
        returns = pd.DataFrame({
            "AAPL": rng.normal(0.0, sigma, 1000),
            "NVDA": rng.normal(0.0, sigma, 1000),
        })
        result = evaluate_scenario(
            weights={"AAPL": 0.5, "NVDA": 0.5},
            returns_df=returns,
            shocks={"NVDA": 0.0},   # no shock - baseline == shocked
            portfolio_value=100_000.0,
        )
        # Equal weights, uncorrelated: portfolio sigma = sigma / sqrt(2)
        portfolio_sigma = sigma / (2 ** 0.5)
        analytical_var = 1.645 * portfolio_sigma  # ~0.01163
        assert abs(result.var_95 - analytical_var) / analytical_var < 0.25, (
            f"VaR {result.var_95:.5f} deviates >25% from analytical {analytical_var:.5f}"
        )
