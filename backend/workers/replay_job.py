"""Replay job implementation (will be appended to job_worker.py)."""

import json
import logging
import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.portfolios.models import Portfolio, Holding, RiskBudget
from app.market.models import HistoricalPrice
from app.replays.models import Replay, ReplayDailyState, BacktestResult
from app.replays.schemas import BacktestResultResponse
from quant.returns import compute_returns, compute_weights, compute_portfolio_returns, MIN_OBSERVATIONS
from quant.covariance import estimate_covariance, InsufficientDataError
from quant.risk_metrics import compute_risk_estimate
from quant.backtest import run_kupiec_pof_test
from quant.constants import KUPIEC_SIGNIFICANCE_LEVEL

from app.database import async_session_factory

logger = logging.getLogger(__name__)

async def run_replay_job(ctx: dict, replay_id: str) -> None:
    """Execute a historical replay for a portfolio over a stress period."""
    logger.info("Starting replay %s", replay_id)
    
    # 1. Fetch Replay and Portfolio details
    async with async_session_factory() as db:
        replay_uuid = uuid.UUID(replay_id)
        result = await db.execute(
            select(Replay)
            .where(Replay.id == replay_uuid)
            .options(selectinload(Replay.portfolio).selectinload(Portfolio.holdings))
        )
        replay = result.scalar_one_or_none()
        if not replay:
            logger.error("Replay %s not found", replay_id)
            return

        try:
            portfolio = replay.portfolio
            
            budget_res = await db.execute(
                select(RiskBudget).where(RiskBudget.portfolio_id == portfolio.id)
            )
            budget = budget_res.scalar_one_or_none()
            max_cvar = float(budget.max_cvar) if budget else 1_000_000.0

            # 2. Fetch Historical Prices for held symbols
            symbols = [h.symbol for h in portfolio.holdings]
            if not symbols:
                raise ValueError("Portfolio has no holdings.")

            prices_res = await db.execute(
                select(HistoricalPrice)
                .where(HistoricalPrice.symbol.in_(symbols))
                .order_by(HistoricalPrice.trading_date)
            )
            price_records = prices_res.scalars().all()

            if not price_records:
                raise ValueError("No historical prices found for portfolio symbols.")

            # Build DataFrame
            records = [
                {"date": p.trading_date, "symbol": p.symbol, "close": float(p.close)}
                for p in price_records
            ]
            df = pd.DataFrame(records)
            prices_df = df.pivot(index="date", columns="symbol", values="close")
            prices_df = prices_df.dropna(how="all")

            # Check if any symbols are completely missing
            missing = set(symbols) - set(prices_df.columns)
            if missing:
                logger.warning("Symbols missing from replay dataset: %s", missing)

            prices_df = prices_df.ffill().bfill()  # simple forward/back fill for missing days
            available_symbols = list(prices_df.columns)

            daily_states = []
            var_breaches = 0

            # Iterate day by day, starting after MIN_OBSERVATIONS + 1
            # We need at least MIN_OBSERVATIONS to predict VaR for the *next* day.
            for i in range(MIN_OBSERVATIONS + 1, len(prices_df)):
                current_date = prices_df.index[i]
                
                # History UP TO the previous day for computing the prediction
                history_prices = prices_df.iloc[:i]
                
                # The actual return on the current day
                # To get portfolio return on current day, we need returns up to current day
                history_prices_with_current = prices_df.iloc[:i+1]
                
                r_series = compute_returns(history_prices_with_current, kind="log")
                
                # Current holdings quantities
                holdings_dict = {
                    h.symbol: (float(h.quantity), float(history_prices.iloc[-1].get(h.symbol, 0)))
                    for h in portfolio.holdings if h.symbol in available_symbols
                }
                
                weights_dict = compute_weights(holdings_dict)
                weights_arr = np.array([weights_dict.get(sym, 0.0) for sym in available_symbols])
                
                # Portfolio returns up to current day
                r_p = compute_portfolio_returns(r_series, weights_dict)
                
                # Actual return on the current day
                actual_return = r_p.values.iloc[-1]
                actual_loss = -actual_return
                
                # Compute risk estimate using history up to previous day
                # We pass r_series up to previous day, and r_p up to previous day
                r_series_prev = compute_returns(history_prices, kind="log")
                r_p_prev = compute_portfolio_returns(r_series_prev, weights_dict)
                
                try:
                    cov_matrix = estimate_covariance(r_series_prev)
                    risk = compute_risk_estimate(r_p_prev.values, weights_arr, cov_matrix, available_symbols)
                    
                    # Compute portfolio value for CVaR translation
                    port_val = sum(q * p for q, p in holdings_dict.values())
                    cvar_cash = risk.cvar_95 * port_val
                    
                    # Risk State Evaluation
                    utilization = cvar_cash / max_cvar
                    if budget:
                        if utilization > float(budget.breach_threshold):
                            risk_state = "breached"
                        elif utilization > float(budget.high_threshold):
                            risk_state = "high"
                        elif utilization > float(budget.watch_threshold):
                            risk_state = "watch"
                        else:
                            risk_state = "safe"
                    else:
                        risk_state = "safe"

                    if actual_loss > risk.var_95:
                        var_breaches += 1

                    state = ReplayDailyState(
                        replay_id=replay.id,
                        trading_date=current_date,
                        var_95=Decimal(str(risk.var_95)),
                        actual_return=Decimal(str(actual_return)),
                        risk_state=risk_state,
                    )
                    daily_states.append(state)

                except InsufficientDataError:
                    continue
                except Exception as e:
                    logger.warning("Error computing day %s: %s", current_date, e)
                    continue

            # Save daily states
            db.add_all(daily_states)

            # Kupiec test
            total_days = len(daily_states)
            backtest_res = run_kupiec_pof_test(total_days, var_breaches)
            
            bt_record = BacktestResult(
                replay_id=replay.id,
                predicted_breach_rate=Decimal(str(backtest_res.predicted_breach_rate)),
                actual_breach_rate=Decimal(str(backtest_res.actual_breach_rate)),
                kupiec_statistic=Decimal(str(backtest_res.kupiec_statistic)),
                p_value=Decimal(str(backtest_res.p_value)),
                passed=backtest_res.passed,
                is_valid=backtest_res.is_valid,
                reason=backtest_res.reason
            )
            db.add(bt_record)

            replay.status = "complete"
            replay.completed_at = datetime.now(UTC)
            await db.commit()
            
            logger.info("Replay %s completed successfully.", replay_id)

        except Exception as e:
            logger.exception("Replay %s failed: %s", replay_id, e)
            replay.status = "failed"
            await db.commit()
