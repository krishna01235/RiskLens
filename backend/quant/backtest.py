"""quant/backtest.py -- Kupiec Proportion of Failures backtest implementation."""

import math
from dataclasses import dataclass
from typing import Optional

from scipy.stats import chi2

from quant.constants import MIN_KUPIEC_SAMPLE_DAYS, KUPIEC_SIGNIFICANCE_LEVEL


@dataclass
class BacktestResult:
    predicted_breach_rate: float
    actual_breach_rate: float
    kupiec_statistic: float
    p_value: float
    passed: bool
    is_valid: bool
    reason: Optional[str] = None


def run_kupiec_pof_test(
    total_days: int,
    failures: int,
    confidence_level: float = KUPIEC_SIGNIFICANCE_LEVEL,
    significance_level: float = KUPIEC_SIGNIFICANCE_LEVEL,
) -> BacktestResult:
    """Run Kupiec Proportion of Failures (POF) Likelihood Ratio test.
    
    Args:
        total_days: Total number of days in the replay/backtest.
        failures: Number of days the portfolio return breached VaR.
        confidence_level: The VaR confidence level (e.g., 0.95 for 95% VaR).
        significance_level: The significance level for the POF test (e.g., 0.95).
        
    Returns:
        BacktestResult containing the LR statistic, p-value, and pass/fail flag.
    """
    if total_days < MIN_KUPIEC_SAMPLE_DAYS:
        return BacktestResult(
            predicted_breach_rate=1.0 - confidence_level,
            actual_breach_rate=failures / total_days if total_days > 0 else 0.0,
            kupiec_statistic=0.0,
            p_value=0.0,
            passed=False,
            is_valid=False,
            reason=f"Insufficient sample size: {total_days} < {MIN_KUPIEC_SAMPLE_DAYS} days."
        )

    p_expected = 1.0 - confidence_level
    p_obs = failures / total_days

    # Calculate log-likelihoods
    # H0: p = p_expected
    # If failures == 0, N * ln(p) is mathematically undefined (0 * -inf).
    # We use limits: x * ln(x) -> 0 as x -> 0.
    term0_expected = (total_days - failures) * math.log(1 - p_expected)
    term1_expected = failures * math.log(p_expected) if failures > 0 else 0.0
    L0 = term0_expected + term1_expected

    # H1: p = p_obs
    term0_obs = (total_days - failures) * math.log(1 - p_obs) if failures < total_days else 0.0
    term1_obs = failures * math.log(p_obs) if failures > 0 else 0.0
    L1 = term0_obs + term1_obs

    # Likelihood Ratio Statistic
    # If the model is perfectly accurate (p_obs == p_expected), LR = 0
    lr_statistic = 2 * (L1 - L0)
    
    # Ensure it's non-negative due to float precision issues
    lr_statistic = max(0.0, lr_statistic)

    # Asymptotically Chi-Squared with 1 degree of freedom
    # p-value is the probability of observing a statistic this extreme or more
    p_value = 1.0 - chi2.cdf(lr_statistic, df=1)

    # We reject H0 (fail the backtest) if the p-value < (1 - significance_level).
    # e.g., if significance is 95%, we reject if p-value < 0.05.
    alpha = 1.0 - significance_level
    passed = bool(p_value >= alpha)

    return BacktestResult(
        predicted_breach_rate=p_expected,
        actual_breach_rate=p_obs,
        kupiec_statistic=lr_statistic,
        p_value=float(p_value),
        passed=passed,
        is_valid=True,
    )
