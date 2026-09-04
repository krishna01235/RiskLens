"""replays/schemas.py -- Pydantic models for Replays."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CreateReplayRequest(BaseModel):
    portfolio_id: uuid.UUID
    period_key: str  # e.g. "covid_2020"


class BacktestResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    predicted_breach_rate: Decimal
    actual_breach_rate: Decimal
    kupiec_statistic: Decimal
    p_value: Decimal
    passed: bool


class ReplayDailyStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trading_date: date
    var_95: Decimal
    actual_return: Decimal
    risk_state: str  # e.g., "safe", "warning", "breached"


class ReplayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    portfolio_id: uuid.UUID
    period_key: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    # Relationships (included when available)
    daily_states: Optional[list[ReplayDailyStateResponse]] = None
    backtest_result: Optional[BacktestResultResponse] = None
