"""
quant/garch.py — GARCH(1,1) conditional volatility modeling.
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from arch import arch_model
from quant.constants import MIN_GARCH_OBSERVATIONS

class GarchResult:
    def __init__(
        self,
        volatility: float,
        omega: float | None = None,
        alpha: float | None = None,
        beta: float | None = None,
        is_fallback: bool = False,
    ):
        self.volatility = volatility
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.is_fallback = is_fallback

def fit_garch(returns: np.ndarray | pd.Series) -> GarchResult:
    """
    Fit a GARCH(1,1) model and forecast volatility.
    
    If the series is too short or the solver fails to converge, falls back
    to the historical standard deviation. Returns daily volatility.
    """
    if isinstance(returns, pd.Series):
        arr = returns.values
    else:
        arr = np.asarray(returns)
        
    arr = arr[~np.isnan(arr)]

    # Scale returns by 100 for better numerical stability in arch solver
    # (a standard practice for financial returns)
    scaled_returns = arr * 100.0

    if len(scaled_returns) < MIN_GARCH_OBSERVATIONS:
        # Fallback to historical standard deviation (daily)
        return GarchResult(
            volatility=float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0),
            is_fallback=True
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = arch_model(scaled_returns, vol="Garch", p=1, q=1, rescale=False)
            res = model.fit(disp="off", show_warning=False)
            
            if not getattr(res.optimization_result, "success", True):
                # Fallback if solver didn't converge successfully
                return GarchResult(
                    volatility=float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0),
                    is_fallback=True
                )
        
        # Forecast 1 step ahead
        forecasts = res.forecast(horizon=1, reindex=False)
        # forecast variance is on the scaled scale (100^2), so sqrt it and scale back by 100
        daily_vol_scaled = np.sqrt(forecasts.variance.values[-1, :])[0]
        daily_vol = daily_vol_scaled / 100.0
        
        return GarchResult(
            volatility=float(daily_vol),
            omega=float(res.params.get("omega", 0.0)),
            alpha=float(res.params.get("alpha[1]", 0.0)),
            beta=float(res.params.get("beta[1]", 0.0)),
            is_fallback=False
        )
    except Exception:
        # Catch convergence or optimization errors and fallback safely
        return GarchResult(
            volatility=float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0),
            is_fallback=True
        )

def forecast_volatility(fit: GarchResult, horizon: int = 1) -> float:
    """
    Return the forecasted volatility over a given horizon.
    For simplicity, assuming constant volatility over the horizon, 
    we scale daily volatility by sqrt(horizon).
    """
    return float(fit.volatility * np.sqrt(horizon))
