import asyncio
import pytest
import numpy as np
from app.alerts.decisions_service import generate_and_evaluate_candidates
from quant.risk_metrics import RiskContribution

@pytest.mark.asyncio
async def test_generate_candidates_omission_margin(monkeypatch):
    from app.alerts import decisions_service
    monkeypatch.setattr(decisions_service, "REDUCE_POSITION_MARGIN", 0.15)
    
    # If top risk contributor's margin > REDUCE_POSITION_MARGIN (15%), omit it.
    # We will simulate risk_contributions with a huge gap.
    risk_contributions = [
        RiskContribution(symbol="TSLA", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.60),
        RiskContribution(symbol="AAPL", weight=0.4, mcr=0.0, rc=0.0, rc_pct=0.30),
        RiskContribution(symbol="MSFT", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.10),
    ]

    # TSLA (60%) - AAPL (30%) = 30% > 15%, so TSLA should NOT be omitted.
    # Wait, the spec says:
    # "Define the exact rule for omitting the "reduce largest risk contributor" candidate — 
    # e.g. top contributor's risk-contribution % must exceed the second-highest by a defined margin...
    # Implement and test both the omitted and included cases."
    # My rule in `decisions_service.py`:
    # margin = sorted_rcs[0].rc_pct - sorted_rcs[1].rc_pct
    # if margin <= REDUCE_POSITION_MARGIN:
    #     candidates.pop(0) # Omit if margin is small
    
    # Setup mock params
    n = 3
    horizon_days = 30
    weights = np.array([0.3, 0.4, 0.3])
    current_values = np.array([3000, 4000, 3000])
    mean_daily_returns = np.zeros(n)
    cov_matrix = np.eye(n) * 0.0001
    garch_vols = {0: 0.2, 1: 0.15, 2: 0.1}
    symbols = ["TSLA", "AAPL", "MSFT"]

    # Case 1: Gap = 30% > 15%, should include "Reduce Position: TSLA"
    candidates = await generate_and_evaluate_candidates(
        horizon_days=horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
        risk_contributions=risk_contributions
    )
    labels = [c.label for c in candidates]
    assert "Reduce TSLA" in labels

    # Case 2: Gap = 5% <= 15%, should OMIT "Reduce Position: TSLA"
    risk_contributions_2 = [
        RiskContribution(symbol="TSLA", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.40),
        RiskContribution(symbol="AAPL", weight=0.4, mcr=0.0, rc=0.0, rc_pct=0.35),
        RiskContribution(symbol="MSFT", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.25),
    ]
    candidates_2 = await generate_and_evaluate_candidates(
        horizon_days=horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
        risk_contributions=risk_contributions_2
    )
    labels_2 = [c.label for c in candidates_2]
    assert "Reduce TSLA" not in labels_2

@pytest.mark.asyncio
async def test_generate_candidates_timeout_fallback(monkeypatch):
    from app.alerts import decisions_service
    original_run = decisions_service.run_simulation
    
    def slow_run(*args, **kwargs):
        import time
        time.sleep(2)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(decisions_service, "run_simulation", slow_run)
    monkeypatch.setattr(decisions_service, "CANDIDATE_MC_TIMEOUT", 0.5)

    n = 3
    horizon_days = 30
    weights = np.array([0.3, 0.4, 0.3])
    current_values = np.array([3000, 4000, 3000])
    mean_daily_returns = np.zeros(n)
    cov_matrix = np.eye(n) * 0.0001
    garch_vols = {0: 0.2, 1: 0.15, 2: 0.1}
    symbols = ["TSLA", "AAPL", "MSFT"]
    risk_contributions = [
        RiskContribution(symbol="TSLA", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.60),
        RiskContribution(symbol="AAPL", weight=0.4, mcr=0.0, rc=0.0, rc_pct=0.30),
        RiskContribution(symbol="MSFT", weight=0.3, mcr=0.0, rc=0.0, rc_pct=0.10),
    ]

    candidates = await generate_and_evaluate_candidates(
        horizon_days=horizon_days,
        weights=weights,
        current_values=current_values,
        mean_daily_returns=mean_daily_returns,
        cov_matrix=cov_matrix,
        garch_vols=garch_vols,
        symbols=symbols,
        risk_contributions=risk_contributions
    )

    # All should fallback since they all sleep for 2s and timeout is 0.5s
    for c in candidates:
        assert c.is_fallback is True
