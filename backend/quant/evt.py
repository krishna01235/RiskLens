"""
quant/evt.py — Extreme Value Theory (EVT) tail-risk estimation.

Computes a Generalized Pareto Distribution (GPD) fit over the right tail of
portfolio losses (which correspond to the left tail of returns). This provides
a Peak-Over-Threshold (POT) VaR and CVaR estimate.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.stats import genpareto
from backend.quant.constants import MIN_EVT_EXCEEDANCES


@dataclass(frozen=True)
class EVTFit:
    """Result of an EVT GPD fit."""
    is_valid: bool
    message: str
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None


def fit_evt(returns: np.ndarray, threshold_quantile: float = 0.90, confidence: float = 0.95) -> EVTFit:
    """
    Fits a GPD to the upper tail of the loss distribution (negative returns).
    
    Parameters
    ----------
    returns : np.ndarray
        1D array of daily portfolio returns.
    threshold_quantile : float
        The quantile at which to set the threshold (e.g., 0.90 means the worst 10%
        of returns are considered the tail).
    confidence : float
        The confidence level for VaR/CVaR (e.g., 0.95).
        
    Returns
    -------
    EVTFit
        An object containing the fitted VaR and CVaR, or a fallback message if
        the fit could not be completed.
    """
    if len(returns) == 0:
        return EVTFit(is_valid=False, message="No return data provided.")
        
    # We focus on the right tail of losses
    losses = -returns
    
    # Determine the threshold value
    u = float(np.quantile(losses, threshold_quantile))
    
    # Extract exceedances
    exceedances = losses[losses > u] - u
    
    if len(exceedances) < MIN_EVT_EXCEEDANCES:
        return EVTFit(
            is_valid=False, 
            message=f"EVT estimate unavailable: requires at least {MIN_EVT_EXCEEDANCES} tail exceedances, but got {len(exceedances)}."
        )

    # Scipy fits shape (c) and scale. Location is fixed to 0 because exceedances are already shifted.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Fit GPD. floc=0 fixes the location parameter at 0.
            c, loc, scale = genpareto.fit(exceedances, floc=0)
            
            if scale <= 0:
                return EVTFit(is_valid=False, message="EVT estimate unavailable: solver returned non-positive scale.")
                
            # Ratio of tail events for the target confidence
            # e.g., if threshold is 90% (q=0.9) and we want 95% (alpha=0.95), tail_prob = 1 - 0.9 = 0.1
            # tail_ratio = (1 - alpha) / (1 - q)
            tail_ratio = (1.0 - confidence) / (1.0 - threshold_quantile)
            
            # Prevent negative base in case of extreme inputs
            if tail_ratio <= 0:
                return EVTFit(is_valid=False, message="Invalid confidence / threshold ratio.")

            if abs(c) < 1e-6:
                # Limit as shape -> 0 (Exponential distribution)
                var = u - scale * np.log(tail_ratio)
                cvar = var + scale
            else:
                var = u + (scale / c) * (tail_ratio**(-c) - 1.0)
                cvar = (var + scale - c * u) / (1.0 - c)
                
            # If shape parameter >= 1, the mean (and thus CVaR) is infinite
            if c >= 1.0:
                # We cap or reject it, but returning infinite CVaR might break the UI.
                return EVTFit(is_valid=False, message="EVT estimate unavailable: shape parameter >= 1 (infinite expected shortfall).")

            return EVTFit(
                is_valid=True,
                message="OK",
                var_95=float(var),
                cvar_95=float(cvar)
            )
            
    except Exception as e:
        return EVTFit(is_valid=False, message=f"EVT estimate unavailable: GPD solver failed to converge.")
