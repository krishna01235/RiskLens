"""portfolios/router.py — Portfolio ingestion endpoints (§7.2) + /market/symbols stub.

The /market/symbols autocomplete endpoint is a stub here backed by a static list.
It will be moved to app/market/router.py in Phase 6 when the real symbol master
list is built from the Finnhub symbol universe.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.auth.models import User

portfolios_router = APIRouter(tags=["portfolios"])
market_router = APIRouter(tags=["market"])

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


# ── /market/symbols — Phase 5 stub ────────────────────────────────────────────
# This endpoint is backed by a static curated list (50 US + 50 Indian symbols).
# Phase 6 replaces this with a real symbol master list from Finnhub and moves
# the endpoint to app/market/router.py.

_STATIC_SYMBOLS: list[dict] = [
    # ── US — NYSE / NASDAQ ──────────────────────────────────────────────────
    {"symbol": "AAPL",  "name": "Apple Inc.",               "exchange": "NASDAQ"},
    {"symbol": "MSFT",  "name": "Microsoft Corporation",    "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)",  "exchange": "NASDAQ"},
    {"symbol": "AMZN",  "name": "Amazon.com Inc.",          "exchange": "NASDAQ"},
    {"symbol": "NVDA",  "name": "NVIDIA Corporation",       "exchange": "NASDAQ"},
    {"symbol": "META",  "name": "Meta Platforms Inc.",      "exchange": "NASDAQ"},
    {"symbol": "TSLA",  "name": "Tesla Inc.",               "exchange": "NASDAQ"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway B",    "exchange": "NYSE"},
    {"symbol": "JPM",   "name": "JPMorgan Chase & Co.",     "exchange": "NYSE"},
    {"symbol": "JNJ",   "name": "Johnson & Johnson",        "exchange": "NYSE"},
    {"symbol": "V",     "name": "Visa Inc.",                "exchange": "NYSE"},
    {"symbol": "UNH",   "name": "UnitedHealth Group",       "exchange": "NYSE"},
    {"symbol": "XOM",   "name": "ExxonMobil Corporation",   "exchange": "NYSE"},
    {"symbol": "WMT",   "name": "Walmart Inc.",             "exchange": "NYSE"},
    {"symbol": "PG",    "name": "Procter & Gamble Co.",     "exchange": "NYSE"},
    {"symbol": "MA",    "name": "Mastercard Inc.",          "exchange": "NYSE"},
    {"symbol": "LLY",   "name": "Eli Lilly and Company",   "exchange": "NYSE"},
    {"symbol": "CVX",   "name": "Chevron Corporation",      "exchange": "NYSE"},
    {"symbol": "HD",    "name": "Home Depot Inc.",          "exchange": "NYSE"},
    {"symbol": "ABBV",  "name": "AbbVie Inc.",              "exchange": "NYSE"},
    {"symbol": "MRK",   "name": "Merck & Co. Inc.",         "exchange": "NYSE"},
    {"symbol": "KO",    "name": "Coca-Cola Company",        "exchange": "NYSE"},
    {"symbol": "COST",  "name": "Costco Wholesale Corp.",   "exchange": "NASDAQ"},
    {"symbol": "PEP",   "name": "PepsiCo Inc.",             "exchange": "NASDAQ"},
    {"symbol": "BAC",   "name": "Bank of America Corp.",    "exchange": "NYSE"},
    {"symbol": "ADBE",  "name": "Adobe Inc.",               "exchange": "NASDAQ"},
    {"symbol": "NFLX",  "name": "Netflix Inc.",             "exchange": "NASDAQ"},
    {"symbol": "CRM",   "name": "Salesforce Inc.",          "exchange": "NYSE"},
    {"symbol": "ORCL",  "name": "Oracle Corporation",       "exchange": "NYSE"},
    {"symbol": "AMD",   "name": "Advanced Micro Devices",   "exchange": "NASDAQ"},
    {"symbol": "INTC",  "name": "Intel Corporation",        "exchange": "NASDAQ"},
    {"symbol": "CSCO",  "name": "Cisco Systems Inc.",       "exchange": "NASDAQ"},
    {"symbol": "PFE",   "name": "Pfizer Inc.",              "exchange": "NYSE"},
    {"symbol": "TMO",   "name": "Thermo Fisher Scientific", "exchange": "NYSE"},
    {"symbol": "DIS",   "name": "Walt Disney Company",      "exchange": "NYSE"},
    {"symbol": "PYPL",  "name": "PayPal Holdings Inc.",     "exchange": "NASDAQ"},
    {"symbol": "QCOM",  "name": "Qualcomm Inc.",            "exchange": "NASDAQ"},
    {"symbol": "T",     "name": "AT&T Inc.",                "exchange": "NYSE"},
    {"symbol": "VZ",    "name": "Verizon Communications",   "exchange": "NYSE"},
    {"symbol": "GS",    "name": "Goldman Sachs Group",      "exchange": "NYSE"},
    {"symbol": "MS",    "name": "Morgan Stanley",           "exchange": "NYSE"},
    {"symbol": "BKNG",  "name": "Booking Holdings Inc.",    "exchange": "NASDAQ"},
    {"symbol": "SBUX",  "name": "Starbucks Corporation",    "exchange": "NASDAQ"},
    {"symbol": "NOW",   "name": "ServiceNow Inc.",          "exchange": "NYSE"},
    {"symbol": "INTU",  "name": "Intuit Inc.",              "exchange": "NASDAQ"},
    {"symbol": "AMAT",  "name": "Applied Materials Inc.",   "exchange": "NASDAQ"},
    {"symbol": "MU",    "name": "Micron Technology Inc.",   "exchange": "NASDAQ"},
    {"symbol": "TXN",   "name": "Texas Instruments Inc.",   "exchange": "NASDAQ"},
    {"symbol": "SPGI",  "name": "S&P Global Inc.",          "exchange": "NYSE"},
    {"symbol": "BLK",   "name": "BlackRock Inc.",           "exchange": "NYSE"},
    # ── India — NSE ─────────────────────────────────────────────────────────
    # Phase 6 note: Finnhub uses "<SYMBOL>.NS" format; stored here without suffix.
    {"symbol": "RELIANCE",    "name": "Reliance Industries Ltd.",     "exchange": "NSE"},
    {"symbol": "TCS",         "name": "Tata Consultancy Services",    "exchange": "NSE"},
    {"symbol": "HDFCBANK",    "name": "HDFC Bank Ltd.",               "exchange": "NSE"},
    {"symbol": "INFY",        "name": "Infosys Ltd.",                 "exchange": "NSE"},
    {"symbol": "ICICIBANK",   "name": "ICICI Bank Ltd.",              "exchange": "NSE"},
    {"symbol": "HINDUNILVR",  "name": "Hindustan Unilever Ltd.",      "exchange": "NSE"},
    {"symbol": "BAJFINANCE",  "name": "Bajaj Finance Ltd.",           "exchange": "NSE"},
    {"symbol": "SBIN",        "name": "State Bank of India",         "exchange": "NSE"},
    {"symbol": "WIPRO",       "name": "Wipro Ltd.",                  "exchange": "NSE"},
    {"symbol": "KOTAKBANK",   "name": "Kotak Mahindra Bank Ltd.",    "exchange": "NSE"},
    {"symbol": "BHARTIARTL",  "name": "Bharti Airtel Ltd.",          "exchange": "NSE"},
    {"symbol": "LT",          "name": "Larsen & Toubro Ltd.",        "exchange": "NSE"},
    {"symbol": "ASIANPAINT",  "name": "Asian Paints Ltd.",           "exchange": "NSE"},
    {"symbol": "AXISBANK",    "name": "Axis Bank Ltd.",              "exchange": "NSE"},
    {"symbol": "MARUTI",      "name": "Maruti Suzuki India Ltd.",    "exchange": "NSE"},
    {"symbol": "SUNPHARMA",   "name": "Sun Pharmaceutical Industries","exchange": "NSE"},
    {"symbol": "TITAN",       "name": "Titan Company Ltd.",          "exchange": "NSE"},
    {"symbol": "ULTRACEMCO",  "name": "UltraTech Cement Ltd.",       "exchange": "NSE"},
    {"symbol": "NESTLEIND",   "name": "Nestle India Ltd.",           "exchange": "NSE"},
    {"symbol": "POWERGRID",   "name": "Power Grid Corp. of India",   "exchange": "NSE"},
    {"symbol": "HCLTECH",     "name": "HCL Technologies Ltd.",       "exchange": "NSE"},
    {"symbol": "TATAMOTORS",  "name": "Tata Motors Ltd.",            "exchange": "NSE"},
    {"symbol": "TECHM",       "name": "Tech Mahindra Ltd.",          "exchange": "NSE"},
    {"symbol": "ONGC",        "name": "Oil & Natural Gas Corp.",     "exchange": "NSE"},
    {"symbol": "NTPC",        "name": "NTPC Ltd.",                   "exchange": "NSE"},
    {"symbol": "ADANIPORTS",  "name": "Adani Ports & SEZ Ltd.",      "exchange": "NSE"},
    {"symbol": "JSWSTEEL",    "name": "JSW Steel Ltd.",              "exchange": "NSE"},
    {"symbol": "TATASTEEL",   "name": "Tata Steel Ltd.",             "exchange": "NSE"},
    {"symbol": "COALINDIA",   "name": "Coal India Ltd.",             "exchange": "NSE"},
    {"symbol": "DIVISLAB",    "name": "Divi's Laboratories Ltd.",    "exchange": "NSE"},
    {"symbol": "DRREDDY",     "name": "Dr. Reddy's Laboratories",    "exchange": "NSE"},
    {"symbol": "EICHERMOT",   "name": "Eicher Motors Ltd.",          "exchange": "NSE"},
    {"symbol": "GRASIM",      "name": "Grasim Industries Ltd.",      "exchange": "NSE"},
    {"symbol": "HEROMOTOCO",  "name": "Hero MotoCorp Ltd.",          "exchange": "NSE"},
    {"symbol": "INDUSINDBK",  "name": "IndusInd Bank Ltd.",          "exchange": "NSE"},
    {"symbol": "ITC",         "name": "ITC Ltd.",                    "exchange": "NSE"},
    {"symbol": "M&M",         "name": "Mahindra & Mahindra Ltd.",    "exchange": "NSE"},
    {"symbol": "BRITANNIA",   "name": "Britannia Industries Ltd.",   "exchange": "NSE"},
    {"symbol": "BAJAJFINSV",  "name": "Bajaj Finserv Ltd.",          "exchange": "NSE"},
    {"symbol": "CIPLA",       "name": "Cipla Ltd.",                  "exchange": "NSE"},
    {"symbol": "BPCL",        "name": "Bharat Petroleum Corp.",      "exchange": "NSE"},
    {"symbol": "APOLLOHOSP",  "name": "Apollo Hospitals Enterprise", "exchange": "NSE"},
    {"symbol": "TATACONSUM",  "name": "Tata Consumer Products Ltd.", "exchange": "NSE"},
    {"symbol": "HINDALCO",    "name": "Hindalco Industries Ltd.",    "exchange": "NSE"},
    {"symbol": "SBILIFE",     "name": "SBI Life Insurance Co. Ltd.", "exchange": "NSE"},
    {"symbol": "HDFCLIFE",    "name": "HDFC Life Insurance Co.",     "exchange": "NSE"},
    {"symbol": "PIDILITIND",  "name": "Pidilite Industries Ltd.",    "exchange": "NSE"},
    {"symbol": "SIEMENS",     "name": "Siemens Ltd.",                "exchange": "NSE"},
    {"symbol": "ZOMATO",      "name": "Zomato Ltd.",                 "exchange": "NSE"},
    {"symbol": "NYKAA",       "name": "FSN E-Commerce (Nykaa)",      "exchange": "NSE"},
]

_EXCHANGE_FILTER_MAP: dict[ExchangeFilter, set[str]] = {
    ExchangeFilter.us: {"NYSE", "NASDAQ"},
    ExchangeFilter.india: {"NSE", "BSE"},
    ExchangeFilter.all: {"NYSE", "NASDAQ", "NSE", "BSE"},
}


@market_router.get("/symbols", response_model=list[SymbolSuggestion])
async def symbol_autocomplete(
    query: str = Query(default="", max_length=20),
    exchange: ExchangeFilter = Query(default=ExchangeFilter.all),
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[SymbolSuggestion]:
    """Return symbol suggestions filtered by query string and exchange.

    Phase 5 stub backed by a static list.  Phase 6 replaces this with a
    real Finnhub symbol master search in app/market/router.py.
    """
    allowed_exchanges = _EXCHANGE_FILTER_MAP[exchange]
    q = query.upper().strip()

    matches = [
        SymbolSuggestion(**s)
        for s in _STATIC_SYMBOLS
        if s["exchange"] in allowed_exchanges
        and (not q or q in s["symbol"] or q.lower() in s["name"].lower())
    ]
    return matches[:20]  # cap at 20 results
