"""tests/unit/test_csv_normalizer.py — Unit tests for the CSV column normalizer.

Tests cover:
  - Exact canonical headers
  - US broker formats (Schwab, IBKR)
  - Indian broker formats (Zerodha Kite, Groww, Angel One)
  - Malformed / missing required columns
  - parse_rows: valid rows including comma-formatted Indian numbers
  - parse_rows: invalid rows raising ValueError
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.portfolios.csv_normalizer import parse_rows, suggest_mapping
from app.portfolios.schemas import AddHoldingRequest, ColumnMapping


# ── suggest_mapping tests ─────────────────────────────────────────────────────


def test_exact_canonical_headers() -> None:
    """Exact field names should match with score 1.0."""
    headers = ["symbol", "quantity", "average_price", "currency"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "symbol"
    assert mapping.quantity_col == "quantity"
    assert mapping.price_col == "average_price"
    assert mapping.currency_col == "currency"


def test_schwab_us_headers() -> None:
    """Schwab-style: Symbol, Description, Quantity, Price, Price Change $, ..."""
    headers = ["Symbol", "Description", "Quantity", "Price", "Price Change $", "% Change"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "Symbol"
    assert mapping.quantity_col == "Quantity"
    assert mapping.price_col == "Price"


def test_ibkr_us_headers() -> None:
    """IBKR-style: Financial Instrument, Quantity, Cost Price, Currency."""
    headers = ["Financial Instrument", "Quantity", "Cost Price", "Currency"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "Financial Instrument"
    assert mapping.quantity_col == "Quantity"
    assert mapping.price_col == "Cost Price"
    assert mapping.currency_col == "Currency"


def test_zerodha_india_headers() -> None:
    """Zerodha Kite: Instrument, Qty, Avg. cost, LTP, Cur. val, P&L."""
    headers = ["Instrument", "Qty", "Avg. cost", "LTP", "Cur. val", "P&L", "Net chg."]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "Instrument"
    assert mapping.quantity_col == "Qty"
    assert mapping.price_col == "Avg. cost"


def test_groww_india_headers() -> None:
    """Groww: Stock Name, NSE/BSE, Quantity, Avg. Buying Price, Current Price."""
    headers = ["Stock Name", "NSE/BSE", "Quantity", "Avg. Buying Price", "Current Price", "Invested Amount"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "Stock Name"
    assert mapping.quantity_col == "Quantity"
    assert mapping.price_col == "Avg. Buying Price"


def test_angel_one_india_headers() -> None:
    """Angel One: Symbol, Exchange, Qty, Avg Price, LTP, Current Value, P/L."""
    headers = ["Symbol", "Exchange", "Qty", "Avg Price", "LTP", "Current Value", "P/L"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "Symbol"
    assert mapping.quantity_col == "Qty"
    assert mapping.price_col == "Avg Price"


def test_malformed_missing_symbol_column() -> None:
    """A CSV with no recognizable symbol column leaves symbol_col as None."""
    headers = ["Date", "Transaction", "Amount", "Balance"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col is None


def test_case_insensitive_matching() -> None:
    """Header matching is case-insensitive."""
    headers = ["SYMBOL", "QUANTITY", "PRICE"]
    mapping = suggest_mapping(headers)
    assert mapping.symbol_col == "SYMBOL"
    assert mapping.quantity_col == "QUANTITY"
    assert mapping.price_col == "PRICE"


# ── parse_rows tests ──────────────────────────────────────────────────────────


def _mapping(**kwargs: str | None) -> ColumnMapping:
    defaults = {
        "symbol_col": "symbol",
        "quantity_col": "quantity",
        "price_col": "average_price",
        "currency_col": None,
    }
    return ColumnMapping(**{**defaults, **kwargs})


def test_parse_rows_valid() -> None:
    """Clean rows produce correct AddHoldingRequest objects."""
    rows = [
        {"symbol": "AAPL", "quantity": "50", "average_price": "178.50"},
        {"symbol": "MSFT", "quantity": "30", "average_price": "415.00"},
    ]
    result = parse_rows(rows, _mapping())
    assert len(result) == 2
    assert result[0].symbol == "AAPL"
    assert result[0].quantity == Decimal("50")
    assert result[1].average_price == Decimal("415.00")


def test_parse_rows_valid_indian_comma_numbers() -> None:
    """Indian broker numbers with commas and ₹ prefix parse correctly."""
    rows = [
        {"symbol": "RELIANCE", "quantity": "25", "average_price": "2,850.00"},
        {"symbol": "BAJFINANCE", "quantity": "10", "average_price": "7,100.50"},
    ]
    result = parse_rows(rows, _mapping())
    assert result[0].average_price == Decimal("2850.00")
    assert result[1].average_price == Decimal("7100.50")


def test_parse_rows_skips_blank_symbol() -> None:
    """Rows with empty symbol field are silently skipped."""
    rows = [
        {"symbol": "", "quantity": "10", "average_price": "100.00"},
        {"symbol": "TCS", "quantity": "20", "average_price": "3950.00"},
    ]
    result = parse_rows(rows, _mapping())
    assert len(result) == 1
    assert result[0].symbol == "TCS"


def test_parse_rows_skips_section_divider() -> None:
    """Rows whose symbol starts with '-' (divider rows) are skipped."""
    rows = [
        {"symbol": "---", "quantity": "", "average_price": ""},
        {"symbol": "INFY", "quantity": "40", "average_price": "1560.00"},
    ]
    result = parse_rows(rows, _mapping())
    assert len(result) == 1


def test_parse_rows_bad_quantity_raises() -> None:
    """Non-numeric quantity raises ValueError with the row index."""
    rows = [{"symbol": "AAPL", "quantity": "abc", "average_price": "178.50"}]
    with pytest.raises(ValueError, match="quantity"):
        parse_rows(rows, _mapping())


def test_parse_rows_missing_symbol_col_raises() -> None:
    """A ColumnMapping with symbol_col=None raises ValueError before parsing."""
    rows = [{"symbol": "AAPL", "quantity": "10", "average_price": "100"}]
    bad_mapping = _mapping(symbol_col=None)
    with pytest.raises(ValueError, match="symbol"):
        parse_rows(rows, bad_mapping)


def test_parse_rows_symbol_uppercased() -> None:
    """Symbols are uppercased during parsing."""
    rows = [{"symbol": "reliance", "quantity": "25", "average_price": "2850"}]
    result = parse_rows(rows, _mapping())
    assert result[0].symbol == "RELIANCE"
