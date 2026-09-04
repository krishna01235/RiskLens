"""app/ai/schemas.py — Pydantic request/response models for the AI endpoints.

All inputs are strictly validated here. The LangGraph agent receives structured
data; if Pydantic rejects the input, no LLM call is made.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ExplainRequest(BaseModel):
    """Request to explain the current risk state for a portfolio."""

    portfolio_id: uuid.UUID
    conversation_id: uuid.UUID | None = None  # continue an existing thread


class WhatIfRequest(BaseModel):
    """Request to evaluate a natural-language what-if question."""

    portfolio_id: uuid.UUID
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Free-text what-if question (max 500 characters).",
    )
    conversation_id: uuid.UUID | None = None  # continue an existing thread


class ShocksPayload(BaseModel):
    """Typed shock dictionary extracted from the model's tool call.

    Used only by the LangGraph tool layer to validate the model's output
    before calling evaluate_scenario. The model must produce this structure;
    if it cannot, validation fails and it receives an error, not a number.
    """

    shocks: dict[str, float] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="symbol -> fractional shock, e.g. {'NVDA': -0.20}.",
    )

    @field_validator("shocks")
    @classmethod
    def validate_shock_range(cls, v: dict[str, float]) -> dict[str, float]:
        for sym, shock in v.items():
            if not (-1.0 < shock < 1.0):
                raise ValueError(
                    f"Shock for '{sym}' ({shock:.4f}) must be in the open interval (-1, 1). "
                    "A value of -1 would liquidate the entire position."
                )
        return v


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ScenarioResultOut(BaseModel):
    """Structured scenario result returned alongside narration text.

    Numbers come from quant/scenarios.py, never from the AI model.
    """

    shocks: dict[str, float]
    var_95: float
    cvar_95: float
    var_95_baseline: float
    cvar_95_baseline: float
    expected_loss: float
    portfolio_value: float
    insufficient_data: bool


class AiMessageOut(BaseModel):
    """Single message in an AI conversation."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str                              # "user" | "assistant"
    content: str
    structured_scenario: ScenarioResultOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiConversationOut(BaseModel):
    """Conversation header (no messages)."""

    id: uuid.UUID
    portfolio_id: uuid.UUID
    started_at: datetime

    model_config = {"from_attributes": True}


class ExplainResponse(BaseModel):
    """Response from POST /ai/explain."""

    conversation_id: uuid.UUID
    narration: str | None        # None if LLM timed out
    timeout: bool = False


class WhatIfResponse(BaseModel):
    """Response from POST /ai/what-if.

    scenario_result is ALWAYS present when the question was parseable —
    it renders immediately. narration is None if the LLM timed out.
    """

    conversation_id: uuid.UUID
    scenario_result: ScenarioResultOut | None = None  # None if question was ambiguous
    narration: str | None = None           # None if LLM timed out
    clarification_needed: bool = False     # True if agent asked a clarifying question
    clarification_question: str | None = None
    timeout: bool = False
