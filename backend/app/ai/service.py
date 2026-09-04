"""app/ai/service.py — AI Risk Analyst business logic.

Ownership enforcement (ownership-and-security-review skill):
  - Every function that touches user data calls _get_portfolio_owned FIRST.
  - Returns/weights are fetched only after ownership is confirmed.
  - Cross-user probe test is in tests/integration/test_ai_endpoints.py.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import run_explain_graph, run_what_if_graph
from app.ai.models import AiConversation, AiMessage
from app.ai.schemas import (
    AiConversationOut,
    AiMessageOut,
    ExplainResponse,
    ScenarioResultOut,
    WhatIfResponse,
)
from app.config import get_settings
from app.portfolios.models import Holding, Portfolio
from app.portfolios.service import _get_portfolio_owned

logger = logging.getLogger(__name__)
_settings = get_settings()

_RISK_STATE_PREFIX = "risk_state:"
_PRICE_HISTORY_PREFIX = "price_history:"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_conversation(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
) -> AiConversation:
    """Ownership-gated conversation lookup / creation."""
    # Ownership gate FIRST — raises 404/403 if invalid
    await _get_portfolio_owned(db, portfolio_id, user_id)

    if conversation_id is not None:
        result = await db.execute(
            select(AiConversation).where(
                AiConversation.id == conversation_id,
                AiConversation.portfolio_id == portfolio_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv is not None:
            return conv
        # Conversation not found for this portfolio — create a new one
        logger.info("Conversation %s not found; creating new one.", conversation_id)

    conv = AiConversation(portfolio_id=portfolio_id)
    db.add(conv)
    await db.flush()
    return conv


async def _fetch_risk_snapshot(redis: Redis, portfolio_id: uuid.UUID) -> dict:
    """Read the cached risk state from Redis."""
    state = await redis.hgetall(f"{_RISK_STATE_PREFIX}{portfolio_id}")
    if not state:
        return {"portfolio_id": str(portfolio_id), "data_status": "pending"}

    snapshot: dict = {
        "portfolio_id": str(portfolio_id),
        "data_status": "pending",
        "portfolio_value": state.get("portfolio_value"),
        "daily_pnl": state.get("daily_pnl"),
    }
    risk_field = state.get("risk")
    if risk_field:
        risk_data = json.loads(risk_field)
        snapshot["data_status"] = risk_data.get("data_status", "pending")
        snapshot["metrics"] = risk_data.get("metrics")
        snapshot["risk_contributions"] = risk_data.get("risk_contributions", [])
        snapshot["risk_updated_at"] = risk_data.get("risk_updated_at")
    return snapshot


async def _fetch_portfolio_context(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
) -> tuple[dict[str, float], pd.DataFrame, float]:
    """Fetch weights and historical returns for a portfolio.

    Returns:
        (weights_dict, returns_df, portfolio_value)
        On missing price history, returns an empty DataFrame (insufficient_data will be set).
    """
    # Fetch holdings
    result = await db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio_id)
    )
    holdings = list(result.scalars().all())

    if not holdings:
        return {}, pd.DataFrame(), 0.0

    # Compute weights from cost basis
    values = {
        h.symbol: float(h.quantity) * float(h.average_price)
        for h in holdings
    }
    total_value = sum(values.values())
    weights = {sym: v / total_value for sym, v in values.items()} if total_value > 0 else {}

    # Fetch historical prices from Redis
    returns_dict: dict[str, list[float]] = {}
    for symbol in weights:
        raw = await redis.lrange(f"{_PRICE_HISTORY_PREFIX}{symbol}", 0, -1)
        if raw and len(raw) >= 2:
            prices = [float(p) for p in raw]
            rets = [
                (prices[i] - prices[i - 1]) / prices[i - 1]
                for i in range(1, len(prices))
            ]
            returns_dict[symbol] = rets

    if returns_dict:
        min_len = min(len(v) for v in returns_dict.values())
        returns_dict = {k: v[:min_len] for k, v in returns_dict.items()}
        returns_df = pd.DataFrame(returns_dict)
    else:
        returns_df = pd.DataFrame()

    return weights, returns_df, total_value


async def _persist_messages(
    db: AsyncSession,
    conv: AiConversation,
    user_text: str,
    assistant_text: str | None,
    structured_scenario: dict | None = None,
) -> list[AiMessage]:
    """Persist user + assistant messages; return them."""
    user_msg = AiMessage(
        conversation_id=conv.id,
        role="user",
        content=user_text,
    )
    assistant_msg = AiMessage(
        conversation_id=conv.id,
        role="assistant",
        content=assistant_text or "",
        structured_scenario=structured_scenario,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)
    return [user_msg, assistant_msg]


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def run_explain(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
) -> ExplainResponse:
    """Explain the current risk state for a portfolio.

    Ownership is enforced before any data is read or LLM is called.
    """
    conv = await _get_or_create_conversation(db, portfolio_id, user_id, conversation_id)
    risk_snapshot = await _fetch_risk_snapshot(redis, portfolio_id)

    narration, timed_out = await run_explain_graph(
        api_key=_settings.anthropic_api_key,
        risk_snapshot=risk_snapshot,
    )

    user_text = "Explain my current risk state."
    await _persist_messages(db, conv, user_text, narration)

    return ExplainResponse(
        conversation_id=conv.id,
        narration=narration,
        timeout=timed_out,
    )


async def run_what_if(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    question: str,
    conversation_id: uuid.UUID | None,
) -> WhatIfResponse:
    """Evaluate a natural-language what-if question.

    Numbers come ONLY from evaluate_scenario; the LLM narrates the result.
    Ownership is enforced before any data is fetched.
    """
    conv = await _get_or_create_conversation(db, portfolio_id, user_id, conversation_id)
    weights, returns_df, portfolio_value = await _fetch_portfolio_context(
        db, redis, portfolio_id
    )

    weights_json = json.dumps(weights)
    returns_json = returns_df.to_json(orient="dict") if not returns_df.empty else "{}"

    (
        scenario_json,
        narration,
        clarification_needed,
        timed_out,
        clarification_question,
    ) = await run_what_if_graph(
        api_key=_settings.anthropic_api_key,
        question=question,
        weights_json=weights_json,
        returns_json=returns_json,
        portfolio_value=portfolio_value,
    )

    # Parse scenario result for persistence and response
    scenario_out: ScenarioResultOut | None = None
    structured: dict | None = None
    if scenario_json:
        try:
            raw = json.loads(scenario_json)
            raw.pop("instruction", None)
            scenario_out = ScenarioResultOut(**raw)
            structured = raw
        except Exception:
            logger.exception("Failed to parse scenario_result_json")

    await _persist_messages(db, conv, question, narration, structured_scenario=structured)

    return WhatIfResponse(
        conversation_id=conv.id,
        scenario_result=scenario_out,
        narration=narration,
        clarification_needed=clarification_needed,
        clarification_question=clarification_question,
        timeout=timed_out,
    )


async def list_conversations(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[AiConversationOut]:
    """List conversations for a portfolio (ownership-gated)."""
    await _get_portfolio_owned(db, portfolio_id, user_id)
    result = await db.execute(
        select(AiConversation)
        .where(AiConversation.portfolio_id == portfolio_id)
        .order_by(AiConversation.started_at.desc())
    )
    return [AiConversationOut.model_validate(c) for c in result.scalars().all()]


async def list_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[AiMessageOut]:
    """List messages for a conversation (ownership via portfolio join)."""
    # Verify ownership by joining through conversation -> portfolio
    conv_result = await db.execute(
        select(AiConversation).where(AiConversation.id == conversation_id)
    )
    conv = conv_result.scalar_one_or_none()
    if conv is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Ownership gate via the portfolio
    await _get_portfolio_owned(db, conv.portfolio_id, user_id)

    result = await db.execute(
        select(AiMessage)
        .where(AiMessage.conversation_id == conversation_id)
        .order_by(AiMessage.created_at.asc())
    )
    return [AiMessageOut.model_validate(m) for m in result.scalars().all()]
