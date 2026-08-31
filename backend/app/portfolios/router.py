"""portfolios/router.py — Portfolio ingestion endpoints (§7.2) + /market/symbols stub.

The /market/symbols autocomplete endpoint is a stub here backed by a static list.
It will be moved to app/market/router.py in Phase 6 when the real symbol master
list is built from the Finnhub symbol universe.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.database import get_db
from app.deps import get_current_user
from app.portfolios import service
from app.portfolios.schemas import (
    AddHoldingRequest,
    CsvConfirmRequest,
    CsvPreviewResponse,
    DemoMarket,
    ExchangeFilter,
    HoldingOut,
    PortfolioOut,
    SymbolSuggestion,
)

portfolios_router = APIRouter(tags=["portfolios"])

# ── /portfolios/demo ──────────────────────────────────────────────────────────


@portfolios_router.post("/demo", response_model=PortfolioOut, status_code=201)
async def create_demo_portfolio(
    market: DemoMarket = Query(default=DemoMarket.us),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> PortfolioOut:
    """Seed and return a demo portfolio (US or India).

    Idempotent: calling this endpoint twice with the same market returns the
    existing demo portfolio without creating a duplicate.
    """
    portfolio = await service.create_demo_portfolio(db, current_user.id, market)
    return PortfolioOut.model_validate(portfolio)


# ── /portfolios/import/preview ────────────────────────────────────────────────


@portfolios_router.post("/import/preview", response_model=CsvPreviewResponse)
async def csv_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> CsvPreviewResponse:
    """Accept a CSV upload and return a suggested column mapping + row preview.

    No database write occurs at this step — the user must call /import/confirm
    after reviewing (and optionally correcting) the mapping.
    """
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "text/plain"):
        # Be lenient — some OS / browsers report text/plain for .csv
        pass  # accept anyway; parse_csv_bytes will raise if unparseable

    csv_bytes = await file.read()
    if len(csv_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    return service.preview_csv(csv_bytes)


# ── /portfolios/import/confirm ────────────────────────────────────────────────


@portfolios_router.post("/import/confirm", response_model=PortfolioOut, status_code=201)
async def csv_confirm(
    req: CsvConfirmRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> PortfolioOut:
    """Confirm the mapping and import all rows as a new portfolio.

    Returns 422 with per-row details if any row fails validation.
    """
    portfolio = await service.confirm_csv_import(db, current_user.id, req)
    return PortfolioOut.model_validate(portfolio)


# ── /portfolios/{id}/holdings  ────────────────────────────────────────────────


@portfolios_router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingOut,
    status_code=201,
)
async def add_holding(
    portfolio_id: uuid.UUID,
    req: AddHoldingRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> HoldingOut:
    """Add or upsert a holding in the user's portfolio.

    If the portfolio already contains the given symbol, updates quantity and
    average_price rather than creating a duplicate.
    """
    holding = await service.add_holding(db, portfolio_id, current_user.id, req)
    return HoldingOut.model_validate(holding)


@portfolios_router.delete(
    "/{portfolio_id}/holdings/{holding_id}",
    status_code=204,
)
async def delete_holding(
    portfolio_id: uuid.UUID,
    holding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    """Remove a holding from the user's portfolio."""
    await service.delete_holding(db, portfolio_id, holding_id, current_user.id)


# ── /portfolios/{id} ──────────────────────────────────────────────────────────


@portfolios_router.get("/{portfolio_id}", response_model=PortfolioOut)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> PortfolioOut:
    """Return a portfolio with its holdings list.

    403 if the portfolio belongs to another user; 404 if not found.
    """
    portfolio = await service.get_portfolio(db, portfolio_id, current_user.id)
    return PortfolioOut.model_validate(portfolio)



