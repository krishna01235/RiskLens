"""simulations/schemas.py -- Pydantic schemas for the simulations API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# Allowed values (matches spec §4.6)
VALID_HORIZONS: set[int] = {1, 7, 30, 90}
VALID_PATH_COUNTS: set[int] = {10_000, 50_000, 100_000}


class SimulationCreateRequest(BaseModel):
    portfolio_id: uuid.UUID
    horizon_days: Literal[1, 7, 30, 90] = Field(
        description="Simulation horizon in trading days."
    )
    num_paths: Literal[10_000, 50_000, 100_000] = Field(
        description="Number of Monte Carlo paths."
    )


class EVTResultPayload(BaseModel):
    is_valid: bool
    message: str
    var_95: float | None = None
    cvar_95: float | None = None


class SimulationResultPayload(BaseModel):
    """Embedded inside SimulationResponse.results when status=complete."""

    prob_profit: float
    prob_loss: float
    expected_pnl: float
    pnl_p5: float
    pnl_p50: float
    pnl_p95: float
    num_paths: int
    evt: EVTResultPayload | None = None


class SimulationResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    horizon_days: int
    num_paths: int
    status: str  # pending | running | complete | failed
    results: SimulationResultPayload | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
