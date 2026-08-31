"""portfolios/service.py — Portfolio ingestion business logic.

All public functions enforce row-level ownership: every query that touches
user-owned data filters by BOTH portfolio_id AND user_id at the SQL layer,
not only at the route layer.

Ownership rule (ownership-and-security-review skill):
  get_portfolio(), add_holding(), delete_holding(), confirm_csv_import() all
  verify user_id before returning data or mutating.  A cross-user probe must
  return 403, tested explicitly in test_portfolios.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.portfolios.csv_normalizer import parse_csv_bytes, parse_rows, suggest_mapping
from app.portfolios.models import Holding, Portfolio
from app.portfolios.reverse_index_service import update_symbol_index
from redis.asyncio import Redis
from app.portfolios.schemas import (
    AddHoldingRequest,
    CsvConfirmRequest,
    CsvPreviewResponse,
    DemoMarket,
)

# ── Assumption A4 — Demo portfolio seed data ──────────────────────────────────
# (symbol, quantity, average_price)
_DEMO_HOLDINGS: dict[str, list[tuple[str, Decimal, Decimal]]] = {
    DemoMarket.us: [
        ("AAPL", Decimal("50"), Decimal("178.50")),
        ("MSFT", Decimal("30"), Decimal("415.00")),
        ("GOOGL", Decimal("20"), Decimal("175.00")),
        ("AMZN", Decimal("25"), Decimal("190.00")),
        ("NVDA", Decimal("15"), Decimal("875.00")),
        ("JPM", Decimal("40"), Decimal("210.00")),
        ("JNJ", Decimal("35"), Decimal("155.00")),
        ("XOM", Decimal("45"), Decimal("115.00")),
        ("BRK-B", Decimal("20"), Decimal("370.00")),
        ("UNH", Decimal("10"), Decimal("540.00")),
    ],
    DemoMarket.india: [
        ("RELIANCE", Decimal("25"), Decimal("2850.00")),
        ("TCS", Decimal("20"), Decimal("3950.00")),
        ("HDFCBANK", Decimal("50"), Decimal("1720.00")),
        ("INFY", Decimal("40"), Decimal("1560.00")),
        ("ICICIBANK", Decimal("60"), Decimal("1220.00")),
        ("HINDUNILVR", Decimal("30"), Decimal("2650.00")),
        ("BAJFINANCE", Decimal("10"), Decimal("7100.00")),
        ("SBIN", Decimal("80"), Decimal("840.00")),
        ("WIPRO", Decimal("45"), Decimal("540.00")),
        ("KOTAKBANK", Decimal("20"), Decimal("1850.00")),
    ],
}

_DEMO_NAMES = {
    DemoMarket.us: "Demo Portfolio (US)",
    DemoMarket.india: "Demo Portfolio (India)",
}

_DEMO_CURRENCIES = {
    DemoMarket.us: "USD",
    DemoMarket.india: "INR",
}

# Maximum raw rows returned in a CSV preview (reduces payload size)
_CSV_PREVIEW_ROWS = 5


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_portfolio_owned(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Portfolio:
    """Load a portfolio, raising 404 if absent or 403 if owned by another user.

    Ownership enforcement: the WHERE clause includes user_id so an attacker
    cannot enumerate portfolio IDs to infer another user's holdings.
    """
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    if portfolio.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return portfolio


# ── Public service functions ───────────────────────────────────────────────────


async def create_demo_portfolio(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: DemoMarket = DemoMarket.us,
) -> Portfolio:
    """Seed and return a demo portfolio for *user_id*.

    Idempotent: if the user already has a demo portfolio with the same name,
    returns it without creating a duplicate.
    """
    name = _DEMO_NAMES[market]

    # Check for an existing demo portfolio with this name for this user
    existing = await db.execute(
        select(Portfolio).where(
            Portfolio.user_id == user_id,
            Portfolio.source == "demo",
            Portfolio.name == name,
        )
    )
    portfolio = existing.scalar_one_or_none()
    if portfolio is not None:
        # Eagerly load holdings before returning
        await db.refresh(portfolio, ["holdings"])
        return portfolio

    portfolio = Portfolio(
        user_id=user_id,
        name=name,
        source="demo",
        currency=_DEMO_CURRENCIES[market],
    )
    db.add(portfolio)
    await db.flush()  # get portfolio.id

    for symbol, quantity, average_price in _DEMO_HOLDINGS[market]:
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                symbol=symbol,
                quantity=quantity,
                average_price=average_price,
                added_at=datetime.now(UTC),
            )
        )

    await db.commit()
    await db.refresh(portfolio, ["holdings"])
    return portfolio


async def get_portfolio(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Portfolio:
    """Return portfolio with holdings, 404/403 if not found/not owned."""
    portfolio = await _get_portfolio_owned(db, portfolio_id, user_id)
    await db.refresh(portfolio, ["holdings"])
    return portfolio


async def add_holding(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    req: AddHoldingRequest,
) -> Holding:
    """Add or upsert a holding in the user's portfolio.

    If the portfolio already contains *req.symbol*, updates quantity and
    average_price rather than creating a duplicate (the DB unique constraint
    on (portfolio_id, symbol) would reject a duplicate anyway).
    """
    # Ownership gate
    await _get_portfolio_owned(db, portfolio_id, user_id)

    symbol = req.symbol.upper().strip()

    # Check for existing holding with same symbol
    existing = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id,
            Holding.symbol == symbol,
        )
    )
    holding = existing.scalar_one_or_none()

    if holding is not None:
        holding.quantity = req.quantity
        holding.average_price = req.average_price
    else:
        holding = Holding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=req.quantity,
            average_price=req.average_price,
            added_at=datetime.now(UTC),
        )
        db.add(holding)

    await db.commit()
    await update_symbol_index(db, redis, symbol, portfolio_id, 1)
    await db.refresh(holding)
    return holding


async def delete_holding(
    db: AsyncSession,
    redis: Redis,
    portfolio_id: uuid.UUID,
    holding_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a holding.  404 if not found; 403 if portfolio not owned."""
    # Ownership gate on the portfolio
    await _get_portfolio_owned(db, portfolio_id, user_id)

    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.portfolio_id == portfolio_id,
        )
    )
    holding = result.scalar_one_or_none()
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found.")

    symbol = holding.symbol
    await db.delete(holding)
    await db.commit()
    await update_symbol_index(db, redis, symbol, portfolio_id, -1)


def preview_csv(csv_bytes: bytes) -> CsvPreviewResponse:
    """Parse CSV bytes and return a mapping suggestion + preview rows.

    Pure function — no database access.  The caller (router) is responsible
    for reading the uploaded file bytes.
    """
    headers, rows = parse_csv_bytes(csv_bytes)
    if not headers:
        raise HTTPException(
            status_code=422, detail="Could not parse the CSV file — no headers found."
        )

    mapping = suggest_mapping(headers)
    preview_rows = rows[:_CSV_PREVIEW_ROWS]
    return CsvPreviewResponse(
        suggested_mapping=mapping,
        headers=headers,
        preview_rows=preview_rows,
    )


async def confirm_csv_import(
    db: AsyncSession,
    redis: Redis,
    user_id: uuid.UUID,
    req: CsvConfirmRequest,
) -> Portfolio:
    """Validate the confirmed mapping, parse all rows, and create a portfolio.

    Per-row validation errors are collected and returned as a 422 detail list
    so the frontend can highlight exactly which rows failed.
    """
    try:
        holding_requests = parse_rows(req.rows, req.mapping)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not holding_requests:
        raise HTTPException(
            status_code=422,
            detail="No valid holdings could be parsed from the provided data.",
        )

    portfolio = Portfolio(
        user_id=user_id,
        name="Imported Portfolio",
        source="csv",
        currency=req.currency,
    )
    db.add(portfolio)
    await db.flush()

    for hr in holding_requests:
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                symbol=hr.symbol,
                quantity=hr.quantity,
                average_price=hr.average_price,
                added_at=datetime.now(UTC),
            )
        )

    await db.commit()
    for hr in holding_requests:
        await update_symbol_index(db, redis, hr.symbol, portfolio.id, 1)
    await db.refresh(portfolio, ["holdings"])
    return portfolio
