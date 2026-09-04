"""alerts/schemas.py -- Pydantic schemas for risk budget and alerts API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


AlertState = Literal["SAFE", "WATCH", "HIGH", "BREACH"]


class RiskBudgetUpsertRequest(BaseModel):
    """Body for PUT /portfolios/{id}/risk-budget."""

    max_cvar: float = Field(
        gt=0,
        description="Maximum acceptable CVaR in portfolio currency (e.g. 5000.00 = $5,000).",
    )
    watch_threshold: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Utilization fraction that triggers WATCH state (default 60%).",
    )
    high_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Utilization fraction that triggers HIGH state (default 80%).",
    )
    breach_threshold: float = Field(
        default=1.00,
        ge=0.0,
        le=2.0,
        description="Utilization fraction that triggers BREACH state (default 100%).",
    )

    @model_validator(mode="after")
    def thresholds_ordered(self) -> "RiskBudgetUpsertRequest":
        if not (self.watch_threshold < self.high_threshold <= self.breach_threshold):
            raise ValueError(
                "Thresholds must satisfy watch < high <= breach."
            )
        return self


class RiskBudgetResponse(BaseModel):
    portfolio_id: uuid.UUID
    max_cvar: float
    watch_threshold: float
    high_threshold: float
    breach_threshold: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    from_state: str
    to_state: str
    fired_at: datetime
    dismissed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    next_cursor: str | None  # ISO datetime of the oldest item, for keyset pagination


class DecisionCandidate(BaseModel):
    label: str
    expected_return: float
    cvar: float
    p_loss: float
    score: float
    is_fallback: bool = False


class DecisionResponse(BaseModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    candidates: list[DecisionCandidate]
    created_at: datetime

    model_config = {"from_attributes": True}
