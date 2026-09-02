import numpy as np
import pytest
from scipy.stats import t

from quant.evt import fit_evt, MIN_EVT_EXCEEDANCES

def test_evt_insufficient_data():
    """Test fallback when data has too few exceedances."""
    # Generate 100 points, threshold=90% -> 10 exceedances.
    # 10 < MIN_EVT_EXCEEDANCES (20), so it should fail gracefully.
    np.random.seed(42)
    returns = np.random.normal(0, 0.01, 100)
    
    result = fit_evt(returns, threshold_quantile=0.90)
    
    assert not result.is_valid
    assert "unavailable: requires at least" in result.message
    assert result.var_95 is None
    assert result.cvar_95 is None

def test_evt_happy_path_heavy_tails():
    """Test GPD fit on a heavy-tailed distribution (Student-t)."""
    # Generate 1000 points from Student-t with df=3 (heavy tails)
    np.random.seed(42)
    returns = t.rvs(df=3, loc=0, scale=0.01, size=1000)
    
    result = fit_evt(returns, threshold_quantile=0.90, confidence=0.95)
    
    assert result.is_valid
    assert result.message == "OK"
    assert result.var_95 is not None
    assert result.cvar_95 is not None
    assert result.cvar_95 > result.var_95
    assert result.var_95 > 0

def test_evt_no_data():
    """Test empty returns array."""
    returns = np.array([])
    result = fit_evt(returns)
    assert not result.is_valid
    assert "No return data provided" in result.message
