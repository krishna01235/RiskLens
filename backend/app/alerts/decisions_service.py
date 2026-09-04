import asyncio
import uuid
from typing import List
import numpy as np
import scipy.stats as stats
from datetime import datetime, UTC

from app.alerts.schemas import DecisionCandidate, DecisionResponse
from quant.constants import (
    REDUCE_POSITION_PCT,
    INCREASE_CASH_PCT,
    DECISION_LAMBDA,
    REDUCE_POSITION_MARGIN,
    CANDIDATE_MC_TIMEOUT,
)
from quant.monte_carlo import SimulationParams, run_simulation
from quant.risk_metrics import RiskContribution


def evaluate_candidate_deterministic(
    label: str,
    horizon_days: int,
    current_values: np.ndarray,
    mean_daily_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> DecisionCandidate:
    """Fallback deterministic mean-variance evaluation for a candidate."""
    expected_pnl = np.sum(current_values * (np.exp(mean_daily_returns * horizon_days) - 1.0))
    
    # Variance of portfolio P&L over horizon
    # var(PnL) ~ sum_i sum_j (S0_i S0_j cov_ij * T)
    pnl_var = 0.0
    n = len(current_values)
    for i in range(n):
        for j in range(n):
            pnl_var += current_values[i] * current_values[j] * cov_matrix[i, j] * horizon_days
    
    pnl_vol = np.sqrt(max(pnl_var, 0.0))
    
    # Parametric CVaR for Normal Distribution
    alpha = 0.95
    z = stats.norm.ppf(alpha)
    # CVaR of standard normal is pdf(z) / (1 - alpha)
    std_cvar = stats.norm.pdf(z) / (1.0 - alpha)
    cvar = pnl_vol * std_cvar - expected_pnl
    
    # Probability of loss
    if pnl_vol > 0:
        p_loss = stats.norm.cdf(0.0, loc=expected_pnl, scale=pnl_vol)
    else:
        p_loss = 1.0 if expected_pnl < 0 else 0.0
        
    score = expected_pnl - DECISION_LAMBDA * cvar
    
    return DecisionCandidate(
        label=label,
        expected_return=float(expected_pnl),
        cvar=float(cvar),
        p_loss=float(p_loss),
        score=float(score),
        is_fallback=True,
    )


async def evaluate_candidate_mc(
    label: str,
    params: SimulationParams,
) -> DecisionCandidate:
    """Run MC evaluation with timeout, returning DecisionCandidate.
    If it times out, raises asyncio.TimeoutError.
    """
    loop = asyncio.get_running_loop()
    # Run CPU-bound MC in a thread pool
    result = await asyncio.wait_for(
        loop.run_in_executor(None, run_simulation, params),
        timeout=CANDIDATE_MC_TIMEOUT
    )
    
    # Calculate CVaR from the terminal PnL array
    # CVaR is the expected loss given loss > VaR
    # VaR_95 is the 5th percentile of PnL
    var_95 = -result.pnl_p5
    tail_pnl = result.terminal_pnl[result.terminal_pnl <= -var_95]
    if len(tail_pnl) > 0:
        cvar = float(-np.mean(tail_pnl))
    else:
        cvar = float(var_95)
        
    score = result.expected_pnl - DECISION_LAMBDA * cvar
    
    return DecisionCandidate(
        label=label,
        expected_return=result.expected_pnl,
        cvar=cvar,
        p_loss=result.prob_loss,
        score=score,
        is_fallback=False,
    )


async def evaluate_candidate_with_fallback(
    label: str,
    params: SimulationParams,
) -> DecisionCandidate:
    """Try MC, fallback to deterministic on timeout or error."""
    try:
        return await evaluate_candidate_mc(label, params)
    except (asyncio.TimeoutError, Exception) as e:
        # Fallback to deterministic
        return evaluate_candidate_deterministic(
            label=label,
            horizon_days=params.horizon_days,
            current_values=params.current_values,
            mean_daily_returns=params.mean_daily_returns,
            cov_matrix=params.cov_matrix,
        )


async def generate_and_evaluate_candidates(
    horizon_days: int,
    weights: np.ndarray,
    current_values: np.ndarray,
    mean_daily_returns: np.ndarray,
    cov_matrix: np.ndarray,
    garch_vols: dict[int, float],
    symbols: list[str],
    risk_contributions: list[RiskContribution],
) -> list[DecisionCandidate]:
    
    mc_paths = 10_000
    candidates = []
    
    # Candidate 1: Do nothing
    params_do_nothing = SimulationParams(
        num_paths=mc_paths,
        horizon_days=horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
    )
    candidates.append(evaluate_candidate_with_fallback("Do Nothing", params_do_nothing))
    
    # Candidate 2: Reduce largest risk contributor
    # Only if the top contributor's rc_pct exceeds the second highest by REDUCE_POSITION_MARGIN
    if len(risk_contributions) >= 2:
        sorted_rc = sorted(risk_contributions, key=lambda rc: rc.rc_pct, reverse=True)
        top_rc = sorted_rc[0]
        second_rc = sorted_rc[1]
        if (top_rc.rc_pct - second_rc.rc_pct) >= REDUCE_POSITION_MARGIN:
            idx = symbols.index(top_rc.symbol)
            new_values = current_values.copy()
            new_values[idx] *= (1.0 - REDUCE_POSITION_PCT)
            # Recompute weights for the SimulationParams (even though MC uses current_values)
            total_value = np.sum(new_values)
            new_weights = new_values / total_value if total_value > 0 else weights.copy()
            
            params_reduce = SimulationParams(
                num_paths=mc_paths,
                horizon_days=horizon_days,
                weights=new_weights,
                current_values=new_values,
                mean_daily_returns=mean_daily_returns,
                cov_matrix=cov_matrix,
                garch_vols=garch_vols,
                symbols=symbols,
            )
            candidates.append(evaluate_candidate_with_fallback(f"Reduce {top_rc.symbol}", params_reduce))
    elif len(risk_contributions) == 1:
        # If only 1 asset, we can just reduce it.
        top_rc = risk_contributions[0]
        idx = symbols.index(top_rc.symbol)
        new_values = current_values.copy()
        new_values[idx] *= (1.0 - REDUCE_POSITION_PCT)
        total_value = np.sum(new_values)
        new_weights = new_values / total_value if total_value > 0 else weights.copy()
        
        params_reduce = SimulationParams(
            num_paths=mc_paths,
            horizon_days=horizon_days,
            weights=new_weights,
            current_values=new_values,
            mean_daily_returns=mean_daily_returns,
            cov_matrix=cov_matrix,
            garch_vols=garch_vols,
            symbols=symbols,
        )
        candidates.append(evaluate_candidate_with_fallback(f"Reduce {top_rc.symbol}", params_reduce))

    # Candidate 3: Increase cash (shift percentage of all positions to cash)
    new_values_cash = current_values * (1.0 - INCREASE_CASH_PCT)
    total_value_cash = np.sum(new_values_cash)
    new_weights_cash = new_values_cash / total_value_cash if total_value_cash > 0 else weights.copy()
    
    params_cash = SimulationParams(
        num_paths=mc_paths,
        horizon_days=horizon_days,
        weights=new_weights_cash,
        current_values=new_values_cash,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
    )
    candidates.append(evaluate_candidate_with_fallback("Increase Cash", params_cash))
    
    # Run all evaluations concurrently
    results = await asyncio.gather(*candidates)
    
    # Rank by score descending
    ranked = sorted(results, key=lambda c: c.score, reverse=True)
    return ranked
