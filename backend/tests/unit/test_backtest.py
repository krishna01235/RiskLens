"""tests/unit/test_backtest.py -- Unit tests for Kupiec backtest."""

import pytest

from quant.backtest import run_kupiec_pof_test


def test_kupiec_pass():
    # 252 days, 95% VaR -> expected 12.6 breaches
    # 13 breaches is extremely close, should definitely pass
    res = run_kupiec_pof_test(total_days=252, failures=13, confidence_level=0.95, significance_level=0.95)
    
    assert res.is_valid is True
    assert res.passed is True
    assert res.predicted_breach_rate == pytest.approx(0.05)
    assert res.actual_breach_rate == 13 / 252
    assert res.kupiec_statistic >= 0.0
    # p-value should be very high because it's almost exactly expected
    assert res.p_value > 0.05


def test_kupiec_fail_too_many_breaches():
    # 252 days, expected 12.6 breaches
    # 30 breaches is huge -> model is underestimating risk
    res = run_kupiec_pof_test(total_days=252, failures=30, confidence_level=0.95, significance_level=0.95)
    
    assert res.is_valid is True
    assert res.passed is False
    assert res.p_value < 0.05


def test_kupiec_fail_too_few_breaches():
    # 252 days, expected 12.6 breaches
    # 1 breach is extremely low -> model is overestimating risk
    res = run_kupiec_pof_test(total_days=252, failures=1, confidence_level=0.95, significance_level=0.95)
    
    assert res.is_valid is True
    assert res.passed is False
    assert res.p_value < 0.05


def test_kupiec_zero_breaches():
    # Formula edge case where failures = 0
    res = run_kupiec_pof_test(total_days=252, failures=0, confidence_level=0.95, significance_level=0.95)
    assert res.is_valid is True
    # At 252 days, 0 breaches vs 12.6 expected should fail Kupiec at 95% significance
    assert res.passed is False


def test_kupiec_insufficient_sample():
    # MIN_KUPIEC_SAMPLE_DAYS is 63
    res = run_kupiec_pof_test(total_days=50, failures=2, confidence_level=0.95, significance_level=0.95)
    assert res.is_valid is False
    assert res.passed is False
    assert res.p_value == 0.0
    assert "Insufficient sample size" in res.reason
