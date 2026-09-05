"""app/ai/router.py — POST /ai/explain, POST /ai/what-if, and conversation history.

Rate limit (Phase 18 §11): 30 what-if requests per hour per user (key = user ID).
Ownership enforcement is delegated to the service layer.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import service
from app.ai.schemas import (
    AiConversationOut,
    AiMessageOut,
    ExplainRequest,
    ExplainResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.auth.models import User
from app.database import get_db
from app.deps import get_current_user, get_current_user_any, get_redis, limiter

ai_router = APIRouter(prefix="/ai", tags=["ai"])


@ai_router.post("/explain", response_model=ExplainResponse)
async def explain_risk(
    req: ExplainRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis=Depends(get_redis),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ExplainResponse:
    """Explain the current risk state for a portfolio in plain language."""
    return await service.run_explain(
        db=db,
        redis=redis,
        portfolio_id=req.portfolio_id,
        user_id=current_user.id,
        conversation_id=req.conversation_id,
    )


@ai_router.post("/what-if", response_model=WhatIfResponse)
@limiter.limit("30/hour")
async def what_if(
    req: WhatIfRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis=Depends(get_redis),  # noqa: B008
    current_user: User = Depends(get_current_user_any("whatif")),  # noqa: B008
) -> WhatIfResponse:
    """Evaluate a natural-language what-if question (30/hour/IP rate limit).

    The numeric result (scenario_result) always renders even if narration times out.
    """
    return await service.run_what_if(
        db=db,
        redis=redis,
        portfolio_id=req.portfolio_id,
        user_id=current_user.id,
        question=req.question,
        conversation_id=req.conversation_id,
    )


@ai_router.get(
    "/conversations/{portfolio_id}",
    response_model=list[AiConversationOut],
)
async def list_conversations(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[AiConversationOut]:
    """List AI conversations for a portfolio (ownership-scoped)."""
    return await service.list_conversations(db, portfolio_id, current_user.id)


@ai_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[AiMessageOut],
)
async def list_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[AiMessageOut]:
    """List messages in an AI conversation (ownership-scoped)."""
    return await service.list_messages(db, conversation_id, current_user.id)
