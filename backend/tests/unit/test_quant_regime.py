import numpy as np
import pytest

from quant.regime import fit_hmm, forward_probability

def test_hmm_fit_relabels_states_correctly():
    """
    Test that fit_hmm consistently labels the high-variance state as state 1 ("stressed").
    """
    # Create a synthetic series: first half is low variance (calm), second half is high variance (stressed)
    np.random.seed(42)
    calm = np.random.normal(0, 0.005, 500)
    stressed = np.random.normal(0, 0.05, 500) # 10x volatility
    returns = np.concatenate([calm, stressed])
    
    model = fit_hmm(returns)
    
    # State 1 should have the higher variance
    var_0 = model.covars_[0, 0, 0]
    var_1 = model.covars_[1, 0, 0]
    assert var_1 > var_0, "State 1 is not the high-variance (stressed) state"
    
    # Run forward_probability on a calm slice
    # Should give low probability of being stressed
    prob_stressed_calm = forward_probability(model, calm[-50:])
    assert prob_stressed_calm < 0.5, "Calm period should have low stressed probability"
    
    # Run forward_probability on a stressed slice
    prob_stressed_volatile = forward_probability(model, stressed[-50:])
    assert prob_stressed_volatile > 0.5, "Volatile period should have high stressed probability"

def test_hmm_forward_probability_uses_only_past_data():
    """
    Test that forward_probability correctly calculates the filtered probability
    which means it should detect a regime shift immediately at the end of the window.
    """
    np.random.seed(42)
    calm = np.random.normal(0, 0.005, 500)
    stressed = np.random.normal(0, 0.05, 500)
    returns = np.concatenate([calm, stressed])
    
    model = fit_hmm(returns)
    
    # We supply a window that was mostly calm, but ends with a few highly volatile observations
    # The filtered probability should quickly pick up on the transition.
    recent_window = np.concatenate([calm[-40:], stressed[:5]])
    prob = forward_probability(model, recent_window)
    
    # The probability of being stressed should be fairly high because the most recent 
    # observations are large shocks.
    assert prob > 0.4, "Filtered probability failed to detect recent volatility shock"
