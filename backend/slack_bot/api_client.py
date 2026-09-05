"""slack_bot/api_client.py — Thin async HTTP client wrapping the RiskLens REST API.

All methods inject the caller-supplied raw API token as a Bearer header.
The base URL is read from the RISKLENS_API_URL environment variable
(defaults to http://localhost:8000 for local development).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_BASE_URL = os.getenv("RISKLENS_API_URL", "http://localhost:8000")
_TIMEOUT = 15.0  # seconds


def _headers(raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_token}"}


async def get_portfolios(raw_token: str) -> list[dict[str, Any]]:
    """GET /portfolios — returns the user's portfolio list."""
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
        resp = client.get("/portfolios", headers=_headers(raw_token))
        resp.raise_for_status()
        return resp.json()


async def get_risk(raw_token: str, portfolio_id: str) -> dict[str, Any]:
    """GET /portfolios/{id}/risk — returns the cached risk snapshot."""
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"/portfolios/{portfolio_id}/risk", headers=_headers(raw_token)
        )
        resp.raise_for_status()
        return resp.json()


async def get_alerts(raw_token: str, limit: int = 10) -> list[dict[str, Any]]:
    """GET /alerts — returns the most recent alerts for the user."""
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
        resp = await client.get(
            "/alerts", params={"limit": limit}, headers=_headers(raw_token)
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", data)


async def post_what_if(
    raw_token: str,
    portfolio_id: str,
    question: str,
) -> dict[str, Any]:
    """POST /ai/what-if — runs a what-if scenario question."""
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0) as client:
        resp = await client.post(
            "/ai/what-if",
            json={"portfolio_id": portfolio_id, "question": question},
            headers=_headers(raw_token),
        )
        resp.raise_for_status()
        return resp.json()


async def exchange_code(code: str, slack_user_id: str) -> bool:
    """POST /slack/link — exchange a one-time code for a linked API token.

    Returns True on success, raises httpx.HTTPStatusError on failure.
    """
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
        resp = await client.post(
            "/slack/link",
            json={"code": code, "slack_user_id": slack_user_id},
        )
        resp.raise_for_status()
        return resp.json().get("linked", False)
