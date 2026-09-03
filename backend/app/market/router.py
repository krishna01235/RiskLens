"""market/router.py — Market data and symbol endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from pydantic import BaseModel
from redis.asyncio import Redis

from app.auth.models import User
from app.deps import get_current_user, get_redis
from app.market.symbol_master import EXCHANGE_FILTER_MAP, SYMBOL_MASTER
from app.portfolios.schemas import ExchangeFilter, SymbolSuggestion

class MarketRegimeResponse(BaseModel):
    calm_probability: float
    stressed_probability: float
    updated_at: float

market_router = APIRouter(tags=["market"])


@market_router.get("/symbols", response_model=list[SymbolSuggestion])
async def symbol_autocomplete(
    query: str = Query(default="", max_length=20),
    exchange: ExchangeFilter = Query(default=ExchangeFilter.all),
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[SymbolSuggestion]:
    """Return symbol suggestions filtered by query string and exchange.
    
    Uses a static master list of curated symbols.
    """
    allowed_exchanges = EXCHANGE_FILTER_MAP[exchange]
    q = query.upper().strip()

    matches = [
        SymbolSuggestion(**s)
        for s in SYMBOL_MASTER
        if s["exchange"] in allowed_exchanges
        and (not q or q in s["symbol"] or q.lower() in s["name"].lower())
    ]
    return matches[:20]  # cap at 20 results

@market_router.get("/regime", response_model=MarketRegimeResponse)
async def get_market_regime(
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
) -> MarketRegimeResponse:
    """Return the latest HMM market regime probabilities."""
    import json
    data = await redis.get("market:regime_probability")
    if not data:
        # Default if worker hasn't run yet
        return MarketRegimeResponse(
            calm_probability=1.0,
            stressed_probability=0.0,
            updated_at=0.0
        )
    parsed = json.loads(data)
    return MarketRegimeResponse(**parsed)
