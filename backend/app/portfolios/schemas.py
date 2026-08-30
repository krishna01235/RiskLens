"""portfolios/schemas.py — Pydantic request/response models for the portfolios API."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────


class DemoMarket(str, Enum):
    us = "us"
    india = "india"


# ── Holding ───────────────────────────────────────────────────────────────────


class HoldingOut(BaseModel):
    id: uuid.UUID
    symbol: str
    quantity: Decimal
    average_price: Decimal
    added_at: datetime

    model_config = {"from_attributes": True}


# ── Portfolio ─────────────────────────────────────────────────────────────────


class PortfolioOut(BaseModel):
    id: uuid.UUID
    name: str
    source: str
    currency: str
    created_at: datetime
    holdings: list[HoldingOut]

    model_config = {"from_attributes": True}


# ── CSV import ────────────────────────────────────────────────────────────────


class ColumnMapping(BaseModel):
    """Maps canonical holding fields to the actual CSV header strings detected."""

    symbol_col: str | None = None
    quantity_col: str | None = None
    price_col: str | None = None
    currency_col: str | None = None  # optional — many brokers omit it


class CsvPreviewResponse(BaseModel):
    suggested_mapping: ColumnMapping
    headers: list[str]
    preview_rows: list[dict]  # first 5 raw rows for user review


class CsvConfirmRequest(BaseModel):
    """Confirmed mapping + all raw rows returned from the preview step."""

    mapping: ColumnMapping
    rows: list[dict]
    currency: str = Field(default="USD", max_length=3)


# ── Manual entry ──────────────────────────────────────────────────────────────


class AddHoldingRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    average_price: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", max_length=3)


# ── Market symbol autocomplete ────────────────────────────────────────────────


class ExchangeFilter(str, Enum):
    us = "us"
    india = "india"
    all = "all"


class SymbolSuggestion(BaseModel):
    symbol: str
    name: str
    exchange: str  # "NSE" | "NYSE" | "NASDAQ" | "BSE"
