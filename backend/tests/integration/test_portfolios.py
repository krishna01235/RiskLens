"""tests/integration/test_portfolios.py — Integration tests for portfolios API.

Requires a live PostgreSQL database (via DATABASE_URL).
"""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.portfolios.schemas import DemoMarket
from app.auth.models import User
from app.portfolios.models import Holding, Portfolio

# All tests in this module require the database
pytestmark = pytest.mark.asyncio(loop_scope="function")

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def auth_headers(
    async_client: AsyncClient, test_user: User, db_session
) -> dict[str, str]:
    """Return Authorization headers for the test user."""
    from app.auth.service import create_access_token
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_other(
    async_client: AsyncClient, other_test_user: User, db_session
) -> dict[str, str]:
    """Return Authorization headers for a second test user."""
    from app.auth.service import create_access_token
    token = create_access_token(other_test_user.id)
    return {"Authorization": f"Bearer {token}"}


# ── Tests: Demo Portfolio ─────────────────────────────────────────────────────


async def test_demo_us_creates_holdings(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post(
        "/portfolios/demo?market=us", headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Demo Portfolio (US)"
    assert data["currency"] == "USD"
    assert len(data["holdings"]) == 10
    
    # AAPL is one of the US demo holdings
    symbols = [h["symbol"] for h in data["holdings"]]
    assert "AAPL" in symbols


async def test_demo_india_creates_holdings(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post(
        "/portfolios/demo?market=india", headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Demo Portfolio (India)"
    assert data["currency"] == "INR"
    assert len(data["holdings"]) == 10
    
    # RELIANCE is one of the India demo holdings
    symbols = [h["symbol"] for h in data["holdings"]]
    assert "RELIANCE" in symbols


async def test_demo_idempotent(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp1 = await async_client.post(
        "/portfolios/demo?market=us", headers=auth_headers
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    resp2 = await async_client.post(
        "/portfolios/demo?market=us", headers=auth_headers
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    assert id1 == id2


# ── Tests: Holdings CRUD ──────────────────────────────────────────────────────


async def test_add_holding(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 1. Create a demo portfolio to attach the holding to
    resp = await async_client.post("/portfolios/demo", headers=auth_headers)
    portfolio_id = resp.json()["id"]

    # 2. Add a new holding
    payload = {
        "symbol": "TSLA",
        "quantity": "50.5",
        "average_price": "200.00",
        "currency": "USD"
    }
    resp = await async_client.post(
        f"/portfolios/{portfolio_id}/holdings", json=payload, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "TSLA"
    assert float(data["quantity"]) == 50.5
    assert float(data["average_price"]) == 200.0

    # 3. Verify it appears in GET
    resp = await async_client.get(f"/portfolios/{portfolio_id}", headers=auth_headers)
    assert resp.status_code == 200
    symbols = [h["symbol"] for h in resp.json()["holdings"]]
    assert "TSLA" in symbols


async def test_add_holding_upsert(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post("/portfolios/demo", headers=auth_headers)
    portfolio_id = resp.json()["id"]

    payload = {"symbol": "TSLA", "quantity": "50", "average_price": "200"}
    await async_client.post(f"/portfolios/{portfolio_id}/holdings", json=payload, headers=auth_headers)

    # Upsert with new quantity and price
    payload2 = {"symbol": "TSLA", "quantity": "100", "average_price": "210"}
    resp2 = await async_client.post(f"/portfolios/{portfolio_id}/holdings", json=payload2, headers=auth_headers)
    assert resp2.status_code == 201
    
    data = resp2.json()
    assert data["symbol"] == "TSLA"
    assert float(data["quantity"]) == 100.0
    assert float(data["average_price"]) == 210.0


async def test_delete_holding(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await async_client.post("/portfolios/demo", headers=auth_headers)
    portfolio = resp.json()
    portfolio_id = portfolio["id"]
    holding_id = portfolio["holdings"][0]["id"]
    symbol = portfolio["holdings"][0]["symbol"]

    # Delete the holding
    del_resp = await async_client.delete(
        f"/portfolios/{portfolio_id}/holdings/{holding_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = await async_client.get(f"/portfolios/{portfolio_id}", headers=auth_headers)
    symbols = [h["symbol"] for h in get_resp.json()["holdings"]]
    assert symbol not in symbols


# ── Tests: Ownership Enforcement ──────────────────────────────────────────────


async def test_get_portfolio_wrong_user(
    async_client: AsyncClient, auth_headers: dict[str, str], auth_headers_other: dict[str, str]
) -> None:
    # User 1 creates portfolio
    resp = await async_client.post("/portfolios/demo", headers=auth_headers)
    portfolio_id = resp.json()["id"]

    # User 2 tries to GET it
    bad_resp = await async_client.get(f"/portfolios/{portfolio_id}", headers=auth_headers_other)
    assert bad_resp.status_code == 403


async def test_add_holding_wrong_user(
    async_client: AsyncClient, auth_headers: dict[str, str], auth_headers_other: dict[str, str]
) -> None:
    # User 1 creates portfolio
    resp = await async_client.post("/portfolios/demo", headers=auth_headers)
    portfolio_id = resp.json()["id"]

    # User 2 tries to POST a holding to it
    payload = {"symbol": "TSLA", "quantity": "1", "average_price": "10"}
    bad_resp = await async_client.post(
        f"/portfolios/{portfolio_id}/holdings", json=payload, headers=auth_headers_other
    )
    assert bad_resp.status_code == 403


# ── Tests: CSV Import ─────────────────────────────────────────────────────────


async def test_csv_preview_and_confirm(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 1. Preview step (Zerodha-style headers)
    csv_content = (
        "Instrument,Qty,Avg. cost,LTP,Cur. val,P&L\n"
        "RELIANCE,25,2850.00,2900,72500,1250\n"
        "TCS,10,3950.00,4000,40000,500\n"
    ).encode("utf-8")

    files = {"file": ("portfolio.csv", io.BytesIO(csv_content), "text/csv")}
    prev_resp = await async_client.post(
        "/portfolios/import/preview", headers=auth_headers, files=files
    )
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()
    
    mapping = prev_data["suggested_mapping"]
    assert mapping["symbol_col"] == "Instrument"
    assert mapping["quantity_col"] == "Qty"
    assert mapping["price_col"] == "Avg. cost"

    # 2. Confirm step
    confirm_payload = {
        "mapping": mapping,
        "rows": prev_data["preview_rows"],
        "currency": "INR"
    }
    conf_resp = await async_client.post(
        "/portfolios/import/confirm", json=confirm_payload, headers=auth_headers
    )
    assert conf_resp.status_code == 201
    
    portfolio = conf_resp.json()
    assert portfolio["source"] == "csv"
    assert portfolio["currency"] == "INR"
    assert len(portfolio["holdings"]) == 2
    
    symbols = {h["symbol"]: h for h in portfolio["holdings"]}
    assert "RELIANCE" in symbols
    assert float(symbols["RELIANCE"]["quantity"]) == 25.0
    assert float(symbols["RELIANCE"]["average_price"]) == 2850.0
