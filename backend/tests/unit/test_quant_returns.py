"""
tests/unit/test_quant_returns.py

Unit tests for quant/returns.py.

All assertions are against hand-computable reference values on synthetic data
or exact analytical results — NOT just "the function runs without error."
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.returns import (
    compute_portfolio_returns,
    compute_returns,
    compute_weights,
)

# ── Fixtures ───────────────────────────────────────────────────────────────────


def _price_df(prices: dict[str, list[float]]) -> pd.DataFrame:
    """Build a price DataFrame from a symbol → price-list dict."""
    return pd.DataFrame(prices)


# ── compute_returns ────────────────────────────────────────────────────────────


class TestComputeReturns:
    def test_log_returns_single_asset_known_value(self):
        """
        For prices [1, e], the log return is exactly 1.0.
        Reference: r_t = ln(e) - ln(1) = 1 - 0 = 1.
        """
        prices = _price_df({"A": [1.0, np.e]})
        result = compute_returns(prices, kind="log")
        assert result.kind == "log"
        assert result.values.shape == (1, 1)
        np.testing.assert_allclose(result.values["A"].iloc[0], 1.0, rtol=1e-12)

    def test_simple_returns_single_asset_known_value(self):
        """
        For prices [100, 110], the simple return is (110-100)/100 = 0.10.
        """
        prices = _price_df({"A": [100.0, 110.0]})
        result = compute_returns(prices, kind="simple")
        assert result.kind == "simple"
        np.testing.assert_allclose(result.values["A"].iloc[0], 0.10, rtol=1e-12)

    def test_log_returns_multi_asset(self):
        """
        Multi-asset: each column computed independently.
        Reference: ln(110/100) ≈ 0.09531, ln(200/100) ≈ 0.69315.
        """
        prices = _price_df({"A": [100.0, 110.0], "B": [100.0, 200.0]})
        result = compute_returns(prices, kind="log")
        np.testing.assert_allclose(
            result.values["A"].iloc[0], np.log(110 / 100), rtol=1e-12
        )
        np.testing.assert_allclose(
            result.values["B"].iloc[0], np.log(200 / 100), rtol=1e-12
        )

    def test_return_shape_drops_first_row(self):
        """Returned DataFrame should have T-1 rows."""
        prices = _price_df({"A": list(range(1, 11))})
        result = compute_returns(prices)
        assert result.values.shape == (9, 1)

    def test_min_obs_counts_complete_rows(self):
        """min_obs should count rows where all assets have non-NaN returns."""
        # Two assets; one NaN in col B at index 2 (return row 1).
        prices = pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [1.0, np.nan, 3.0]})
        result = compute_returns(prices, kind="simple")
        # returns has 2 rows: row 0 (A=1.0, B=nan), row 1 (A=0.5, B=nan→inf or NaN)
        # Complete rows = 0 because col B always has NaN in returns.
        assert result.min_obs == 0

    def test_raises_on_single_row(self):
        """A single-row price DataFrame cannot produce returns."""
        prices = _price_df({"A": [100.0]})
        with pytest.raises(ValueError, match="at least 2"):
            compute_returns(prices)

    def test_raises_on_unknown_kind(self):
        """Unknown kind should raise ValueError."""
        prices = _price_df({"A": [100.0, 110.0]})
        with pytest.raises(ValueError, match="Unknown return kind"):
            compute_returns(prices, kind="geometric")

    def test_log_returns_are_additive(self):
        """
        Over [P0, P1, P2], the sum of two consecutive log returns equals
        the log return over the full period.
        Reference: ln(P2/P1) + ln(P1/P0) = ln(P2/P0).
        """
        prices = _price_df({"A": [50.0, 60.0, 75.0]})
        result = compute_returns(prices, kind="log")
        r1, r2 = result.values["A"].tolist()
        expected = np.log(75.0 / 50.0)
        np.testing.assert_allclose(r1 + r2, expected, rtol=1e-12)


# ── compute_weights ────────────────────────────────────────────────────────────


class TestComputeWeights:
    def test_equal_holdings_sum_to_one(self):
        """Two equal-value positions → each weight = 0.5."""
        holdings = {"A": (10.0, 100.0), "B": (10.0, 100.0)}
        weights = compute_weights(holdings)
        assert pytest.approx(weights["A"], rel=1e-12) == 0.5
        assert pytest.approx(weights["B"], rel=1e-12) == 0.5
        assert pytest.approx(sum(weights.values()), rel=1e-12) == 1.0

    def test_unequal_holdings_proportional(self):
        """
        A: 1 share × $200 = $200; B: 2 shares × $100 = $200.
        Total = $400; w_A = 0.5, w_B = 0.5.
        """
        holdings = {"A": (1.0, 200.0), "B": (2.0, 100.0)}
        weights = compute_weights(holdings)
        np.testing.assert_allclose(weights["A"], 0.5, rtol=1e-12)
        np.testing.assert_allclose(weights["B"], 0.5, rtol=1e-12)

    def test_single_asset_weight_is_one(self):
        """A portfolio with one asset must have weight = 1.0."""
        weights = compute_weights({"AAPL": (5.0, 180.0)})
        np.testing.assert_allclose(weights["AAPL"], 1.0, rtol=1e-12)

    def test_three_assets_proportional(self):
        """
        A: 1×$100=$100; B: 2×$50=$100; C: 1×$300=$300. Total=$500.
        w_A=0.2, w_B=0.2, w_C=0.6.
        """
        holdings = {"A": (1.0, 100.0), "B": (2.0, 50.0), "C": (1.0, 300.0)}
        weights = compute_weights(holdings)
        np.testing.assert_allclose(weights["A"], 0.2, rtol=1e-12)
        np.testing.assert_allclose(weights["B"], 0.2, rtol=1e-12)
        np.testing.assert_allclose(weights["C"], 0.6, rtol=1e-12)

    def test_raises_on_empty(self):
        with pytest.raises(ValueError, match="must not be empty"):
            compute_weights({})

    def test_raises_on_zero_quantity(self):
        with pytest.raises(ValueError, match="positive"):
            compute_weights({"A": (0.0, 100.0)})

    def test_raises_on_negative_price(self):
        with pytest.raises(ValueError, match="positive"):
            compute_weights({"A": (10.0, -1.0)})


# ── compute_portfolio_returns ──────────────────────────────────────────────────


class TestComputePortfolioReturns:
    def _make_asset_returns(self, data: dict[str, list[float]]):
        from quant.returns import ReturnSeries

        df = pd.DataFrame(data)
        return ReturnSeries(values=df, kind="log", min_obs=len(df))

    def test_single_asset_portfolio_equal_to_asset(self):
        """Single asset, weight=1 → portfolio return = asset return."""
        asset_rets = self._make_asset_returns({"A": [0.01, 0.02, -0.01]})
        weights = {"A": 1.0}
        port = compute_portfolio_returns(asset_rets, weights)
        np.testing.assert_allclose(
            port.values.tolist(), [0.01, 0.02, -0.01], rtol=1e-12
        )

    def test_two_assets_equal_weight(self):
        """
        50/50 portfolio: r_p,t = 0.5 * r_A,t + 0.5 * r_B,t.
        Reference: [0.5*(0.1+0.3), 0.5*(-0.2+0.4)] = [0.2, 0.1]
        """
        asset_rets = self._make_asset_returns({"A": [0.1, -0.2], "B": [0.3, 0.4]})
        weights = {"A": 0.5, "B": 0.5}
        port = compute_portfolio_returns(asset_rets, weights)
        np.testing.assert_allclose(port.values.tolist(), [0.2, 0.1], rtol=1e-12)

    def test_weights_stored_correctly(self):
        """Weights dictionary is preserved on the result."""
        asset_rets = self._make_asset_returns({"A": [0.01], "B": [0.02]})
        weights = {"A": 0.3, "B": 0.7}
        port = compute_portfolio_returns(asset_rets, weights)
        assert port.weights == weights

    def test_raises_on_missing_symbol(self):
        """Weight references a symbol not in the return DataFrame."""
        asset_rets = self._make_asset_returns({"A": [0.01]})
        weights = {"A": 0.5, "MISSING": 0.5}
        with pytest.raises(ValueError, match="not found"):
            compute_portfolio_returns(asset_rets, weights)
