import numpy as np
import pandas as pd
import pytest

from quant.garch import fit_garch, forecast_volatility, MIN_GARCH_OBSERVATIONS

def test_garch_happy_path():
    """Test GARCH fitting on a reasonably sized synthetic series."""
    # Generate synthetic GARCH(1,1) data
    np.random.seed(42)
    n = 1000
    omega, alpha, beta = 0.1, 0.1, 0.8
    returns = np.zeros(n)
    sigma2 = np.zeros(n)
    sigma2[0] = omega / (1 - alpha - beta)
    
    for t in range(1, n):
        sigma2[t] = omega + alpha * returns[t-1]**2 + beta * sigma2[t-1]
        returns[t] = np.random.normal(0, np.sqrt(sigma2[t]))
        
    # the solver works better with realistic return scales (e.g. 1%)
    # the series above is on the "scaled" scale, let's scale it down to simulate
    # raw returns which the function expects
    raw_returns = returns / 100.0

    result = fit_garch(raw_returns)
    
    assert not result.is_fallback
    assert result.omega is not None
    assert result.alpha is not None
    assert result.beta is not None
    assert result.volatility > 0.0

def test_garch_fallback_insufficient_data():
    """Test fallback when data length < MIN_GARCH_OBSERVATIONS."""
    # Create array smaller than minimum
    np.random.seed(42)
    raw_returns = np.random.normal(0, 0.01, MIN_GARCH_OBSERVATIONS - 1)
    
    result = fit_garch(raw_returns)
    
    assert result.is_fallback
    assert result.omega is None
    assert result.alpha is None
    assert result.beta is None
    
    # Check that fallback volatility is the daily standard deviation
    expected_vol = np.std(raw_returns, ddof=1)
    assert np.isclose(result.volatility, expected_vol)

def test_garch_fallback_convergence_error():
    """Test fallback when the solver raises an error or fails to converge."""
    # A flat series or zeros should cause the solver to fail
    raw_returns = np.zeros(100)
    
    result = fit_garch(raw_returns)
    
    assert result.is_fallback
    assert result.volatility == 0.0

def test_forecast_volatility():
    """Test the horizon scaling of the volatility forecast."""
    from quant.garch import GarchResult
    fit = GarchResult(volatility=0.02, is_fallback=False)
    
    # 1 day horizon
    assert forecast_volatility(fit, horizon=1) == 0.02
    
    # 10 day horizon -> vol * sqrt(10)
    assert np.isclose(forecast_volatility(fit, horizon=10), 0.02 * np.sqrt(10))
