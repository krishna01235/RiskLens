"""portfolios/csv_normalizer.py — CSV header fuzzy-matching and row parsing.

Supports US brokers (Schwab, IBKR) and Indian brokers (Zerodha Kite, Groww,
Angel One) via a single canonical alias table and difflib fuzzy matching.

This module has **no database or FastAPI imports** and is fully unit-testable.
"""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from app.portfolios.schemas import AddHoldingRequest, ColumnMapping

# ── Canonical field aliases ────────────────────────────────────────────────────
# Keys are the internal field names; values are known header variants across
# brokers (US and Indian).  All strings are lower-cased at match time.

CANONICAL_FIELDS: dict[str, list[str]] = {
    "symbol": [
        # Generic
        "symbol",
        "ticker",
        "stock",
        "isin",
        "scrip",
        "security",
        "name",
        # US brokers
        "instrument",
        "financial instrument",
        "description",
        # Indian brokers — Zerodha / Angel One
        "trading symbol",
        "tradingsymbol",
        # Indian brokers — Groww
        "stock name",
    ],
    "quantity": [
        "quantity",
        "qty",
        "shares",
        "units",
        "amount",
        "position",
        "no. of shares",
        "no of shares",
        "no.of shares",
        "holdings qty",
        "net qty",
    ],
    "price": [
        # Generic
        "price",
        "avg price",
        "average price",
        "average cost",
        "unit cost",
        "book value",
        # US brokers
        "avg cost",
        "cost price",
        "cost basis",
        # Indian brokers — Zerodha
        "avg. cost",
        "average buying price",
        # Indian brokers — Groww
        "avg. buying price",
        "avg buying price",
        # Indian brokers — Angel One
        "buy avg price",
    ],
    "currency": [
        "currency",
        "ccy",
        "curr",
        "cur",
    ],
}

# Fuzzy-match threshold: scores below this value are ignored.
_FUZZY_THRESHOLD = 0.60


def _normalize(s: str) -> str:
    """Lowercase, strip, and collapse internal whitespace for fuzzy comparison."""
    return re.sub(r"\s+", " ", s.strip().lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def suggest_mapping(headers: list[str]) -> ColumnMapping:
    """Return the best-guess ColumnMapping for the given CSV header row.

    For each canonical field, picks the header with the highest similarity
    score above the threshold.  Returns ``None`` for that field if no header
    qualifies — the user will be prompted to supply it manually.

    Args:
        headers: Raw header strings as read from the CSV file.

    Returns:
        A :class:`ColumnMapping` with matched (or ``None``) column names.
    """
    normalized_headers = [_normalize(h) for h in headers]
    result: dict[str, str | None] = {}

    for field, aliases in CANONICAL_FIELDS.items():
        best_score = 0.0
        best_original: str | None = None

        for idx, norm_header in enumerate(normalized_headers):
            for alias in aliases:
                score = _similarity(norm_header, alias)
                if score > best_score:
                    best_score = score
                    best_original = headers[idx]

        result[f"{field}_col"] = (
            best_original if best_score >= _FUZZY_THRESHOLD else None
        )

    return ColumnMapping(**result)


def _coerce_decimal(raw: str, field: str, row_index: int) -> Decimal:
    """Parse a potentially comma-formatted decimal string.

    Strips currency symbols (₹, $, £) and thousands separators before
    converting, so values like "₹1,250.50" or "2,850.00" parse correctly.
    """
    cleaned = re.sub(r"[^\d.\-]", "", raw.replace(",", ""))
    if not cleaned:
        raise ValueError(
            f"Row {row_index}: field '{field}' is empty or non-numeric (got {raw!r})."
        )
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(
            f"Row {row_index}: cannot parse '{field}' value {raw!r} as a number."
        ) from exc


def parse_rows(
    rows: list[dict],
    mapping: ColumnMapping,
) -> list[AddHoldingRequest]:
    """Convert raw CSV row dicts into validated :class:`AddHoldingRequest` objects.

    Args:
        rows: Raw rows as returned by ``csv.DictReader``.
        mapping: The confirmed column mapping (symbol_col, quantity_col, price_col).

    Returns:
        A list of :class:`AddHoldingRequest` instances.

    Raises:
        ValueError: If a required mapping column is ``None`` or a row value
            is unparseable.  The message includes the row index for actionable
            error display in the frontend.
    """
    if mapping.symbol_col is None:
        raise ValueError("Column mapping for 'symbol' is required before importing.")
    if mapping.quantity_col is None:
        raise ValueError("Column mapping for 'quantity' is required before importing.")
    if mapping.price_col is None:
        raise ValueError(
            "Column mapping for 'average_price' is required before importing."
        )

    results: list[AddHoldingRequest] = []

    for idx, row in enumerate(rows):
        raw_symbol = row.get(mapping.symbol_col, "").strip()

        # Skip obvious header/section-divider rows (e.g. "Equity", "---")
        if not raw_symbol or len(raw_symbol) < 2 or raw_symbol.startswith("-"):
            continue
        # Skip rows where the symbol looks like a section label (e.g. all digits only)
        if raw_symbol.replace(" ", "").isdigit():
            continue

        raw_qty = row.get(mapping.quantity_col, "").strip()
        raw_price = row.get(mapping.price_col, "").strip()

        quantity = _coerce_decimal(raw_qty, "quantity", idx)
        average_price = _coerce_decimal(raw_price, "average_price", idx)

        if quantity <= 0:
            raise ValueError(f"Row {idx}: quantity must be positive (got {quantity}).")
        if average_price <= 0:
            raise ValueError(
                f"Row {idx}: average_price must be positive (got {average_price})."
            )

        results.append(
            AddHoldingRequest(
                symbol=raw_symbol.upper(),
                quantity=quantity,
                average_price=average_price,
            )
        )

    return results


def parse_csv_bytes(csv_bytes: bytes) -> tuple[list[str], list[dict]]:
    """Decode raw CSV bytes and return (headers, rows).

    Attempts UTF-8 decoding first; falls back to latin-1 for files exported
    from older Indian broker platforms that may use that encoding.
    """
    try:
        text = csv_bytes.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        text = csv_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], []

    headers = [str(h) for h in reader.fieldnames]
    rows = [dict(row) for row in reader]
    return headers, rows
