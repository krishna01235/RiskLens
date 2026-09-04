"""
quant/scenarios.py — Deterministic portfolio scenario evaluator.

This is the ONLY function that produces numbers in the AI what-if flow.
The LangGraph agent calls this; it never estimates outcomes itself.

Formula (matching docs/implementation.md §F15 / Phase 18 notation):

  Shocked position value:
    V_i_shocked = V_i * (1 + shock_i)   where shock_i in (-1, 1)

  Re-normalised weights:
    w_i_shocked = V_i_shocked / sum_j(V_j_shocked)

  Shocked portfolio returns:
    r_p_shocked_t = sum_i( w_i_shocked * r_i_t )

  VaR / CVaR:
    Computed via existing historical method on the shocked portfolio return series.

  Expected P&L impact:
    expected_impact = sum_i( w_i_original * portfolio_value * shock_i )
    (first-order approximation; ignores cross-asset effects)

Edge cases:
  - Shock for unknown symbol  -> ValueError (caller/Pydantic handles it)
  - All shocks zero           -> returns unshocked metrics, no change
  - Insufficient observations -> insufficient_data=True, parametric fallback
  - Single-asset portfolio    -> handled (degenerate case)

No I/O inside this module — all functions take plain NumPy/Pandas structures.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.covariance import InsufficientDataError
from quant.returns import MIN_OBSERVATIONS
from quant.risk_metrics import compute_var_cvar


@dataclass(frozen=True)
class ScenarioResult:
    """Result of a deterministic scenario evaluation.

    All numeric fields use the same sign convention as RiskEstimate:
    var_95 and cvar_95 are positive numbers representing losses.
    expected_loss is positive for a net portfolio loss.
    """

    shocks: dict[str, float]      # symbol -> fractional shock (e.g. -0.20)
    var_95: float                  # 1-day 95% historical VaR under shock (loss > 0)
    cvar_95: float                 # 1-day 95% historical CVaR under shock (loss > 0)
    var_95_baseline: float         # unshocked VaR for comparison
    cvar_95_baseline: float        # unshocked CVaR for comparison
    expected_loss: float           # first-order expected P&L impact (positive = loss)
    portfolio_value: float         # total portfolio value used for scaling
    insufficient_data: bool        # True when obs < MIN_OBSERVATIONS


def evaluate_scenario(
    weights: dict[str, float],
    returns_df: pd.DataFrame,
    shocks: dict[str, float],
    portfolio_value: float = 1.0,
) -> ScenarioResult:
    """Apply percentage shocks and recompute VaR/CVaR using the quant engine.

    Parameters
    ----------
    weights:
        Mapping of symbol -> portfolio weight (must sum to ~1).
        Only symbols present here are affected by shocks.
    returns_df:
        DataFrame of daily log returns, columns = symbols, rows = dates.
        Must include all symbols in ``weights``.
    shocks:
        Mapping of symbol -> fractional shock (e.g. {"NVDA": -0.20}).
        Each value must be in (-1.0, 1.0).
        Unknown symbols (not in ``weights``) raise ValueError.
    portfolio_value:
        Total portfolio value in home currency; used to compute expected_loss.

    Returns
    -------
    ScenarioResult with before/after VaR, CVaR, and first-order expected loss.

    Raises
    ------
    ValueError
        If any shock symbol is not in ``weights`` or any shock is out of range.
    """
    # -- Validate shocks -------------------------------------------------------
    for sym, shock in shocks.items():
        if sym not in weights:
            raise ValueError(
                f"Shock symbol '{sym}' is not in the portfolio. "
                f"Known symbols: {sorted(weights)}."
            )
        if not (-1.0 < shock < 1.0):
            raise ValueError(
                f"Shock for '{sym}' ({shock:.4f}) is out of the allowed range (-1, 1). "
                "A shock of -1.0 would liquidate the entire position."
            )

    symbols = list(weights.keys())

    # Ensure returns_df only contains columns we care about (in correct order)
    available = [s for s in symbols if s in returns_df.columns]
    ret_mat = returns_df[available].dropna().to_numpy(dtype=float)

    n_obs = ret_mat.shape[0]
    insufficient = n_obs < MIN_OBSERVATIONS

    # -- Baseline metrics -------------------------------------------------------
    w_avail_orig = np.array([weights[s] for s in available], dtype=float)
    total = w_avail_orig.sum()
    if total > 0:
        w_avail_orig = w_avail_orig / total  # renormalise

    portfolio_returns_orig = ret_mat @ w_avail_orig

    try:
        var_base, cvar_base = compute_var_cvar(portfolio_returns_orig)
    except (InsufficientDataError, ValueError):
        # Parametric 95% VaR fallback when data is thin
        std = float(np.std(portfolio_returns_orig)) if len(portfolio_returns_orig) > 1 else 0.01
        var_base = 1.645 * std
        cvar_base = var_base * 1.25

    # -- Apply shocks to weights ------------------------------------------------
    # Shocked position value = original_weight_i * (1 + shock_i)
    shocked_values = np.array(
        [weights[s] * (1.0 + shocks.get(s, 0.0)) for s in available],
        dtype=float,
    )
    total_shocked = shocked_values.sum()
    if total_shocked <= 0:
        # All positions wiped out — degenerate case
        w_shocked = np.ones(len(available), dtype=float) / max(len(available), 1)
    else:
        w_shocked = shocked_values / total_shocked

    # -- Shocked portfolio returns -----------------------------------------------
    portfolio_returns_shocked = ret_mat @ w_shocked

    try:
        var_95, cvar_95 = compute_var_cvar(portfolio_returns_shocked)
    except (InsufficientDataError, ValueError):
        std = float(np.std(portfolio_returns_shocked)) if len(portfolio_returns_shocked) > 1 else 0.01
        var_95 = 1.645 * std
        cvar_95 = var_95 * 1.25

    # -- First-order expected P&L impact ----------------------------------------
    # expected_impact = sum_i( w_i * portfolio_value * shock_i )
    # Positive impact -> gain, so negate for expected_loss (loss = positive).
    shock_vec = np.array([shocks.get(s, 0.0) for s in available], dtype=float)
    expected_impact = float(w_avail_orig @ shock_vec) * portfolio_value
    expected_loss = -expected_impact  # positive = loss

    return ScenarioResult(
        shocks=dict(shocks),
        var_95=float(var_95),
        cvar_95=float(cvar_95),
        var_95_baseline=float(var_base),
        cvar_95_baseline=float(cvar_base),
        expected_loss=float(expected_loss),
        portfolio_value=float(portfolio_value),
        insufficient_data=insufficient,
    )
