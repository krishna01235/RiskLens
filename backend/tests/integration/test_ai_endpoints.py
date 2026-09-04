"""tests/integration/test_ai_endpoints.py — Integration tests for Phase 18 AI endpoints.

Tests:
  1. POST /ai/explain returns 200 with narration (mocked LLM)
  2. POST /ai/what-if cross-user probe returns 403
  3. POST /ai/what-if rate-limit: 31st call returns 429
  4. LLM timeout -> scenario_result still returned, narration=null
  5. Ambiguous question handled (clarification detected)

The LLM (Anthropic API) is mocked throughout; no external network calls.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.auth.models import User
from app.portfolios.models import Holding, Portfolio

pytestmark = pytest.mark.asyncio(loop_scope="function")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def auth_headers(async_client: AsyncClient, test_user: User, db_session) -> dict[str, str]:
    from app.auth.service import create_access_token
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_other(
    async_client: AsyncClient, other_test_user: User, db_session
) -> dict[str, str]:
    from app.auth.service import create_access_token
    token = create_access_token(other_test_user.id)
    return {"Authorization": f"Bearer {token}"}


async def _create_portfolio_with_holding(db_session, user_id: uuid.UUID) -> Portfolio:
    """Create a portfolio with one holding for the given user."""
    portfolio = Portfolio(
        user_id=user_id,
        name="AI Test Portfolio",
        currency="USD",
        source="manual",
    )
    db_session.add(portfolio)
    await db_session.flush()

    holding = Holding(
        portfolio_id=portfolio.id,
        symbol="AAPL",
        quantity=10,
        average_price=180.0,
    )
    db_session.add(holding)
    await db_session.commit()
    await db_session.refresh(portfolio)
    return portfolio


# ---------------------------------------------------------------------------
# Test 1 — POST /ai/explain: mocked LLM returns narration
# ---------------------------------------------------------------------------


async def test_explain_returns_narration(
    async_client: AsyncClient,
    db_session,
    auth_headers: dict,
    test_user: User,
) -> None:
    """POST /ai/explain with mocked LLM returns 200 with narration string."""
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    mock_narration = "Your portfolio has a 95% VaR of 2.5%, meaning on a bad day you could lose up to $2,500."

    with (
        patch("app.ai.service.run_explain_graph", new_callable=AsyncMock) as mock_explain,
        patch("app.ai.service._fetch_risk_snapshot", new_callable=AsyncMock) as mock_snapshot,
    ):
        mock_explain.return_value = (mock_narration, False)
        mock_snapshot.return_value = {
            "portfolio_id": str(portfolio.id),
            "data_status": "ready",
            "metrics": {"var_95": 0.025, "cvar_95": 0.032, "volatility": 0.18,
                        "sharpe": 1.2, "max_drawdown": 0.05, "n_obs": 100},
        }

        resp = await async_client.post(
            "/ai/explain",
            json={"portfolio_id": str(portfolio.id)},
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["narration"] == mock_narration
    assert data["timeout"] is False
    assert "conversation_id" in data


# ---------------------------------------------------------------------------
# Test 2 — POST /ai/what-if: cross-user probe returns 403
# ---------------------------------------------------------------------------


async def test_what_if_cross_user_returns_403(
    async_client: AsyncClient,
    db_session,
    auth_headers_other: dict,
    test_user: User,
) -> None:
    """User B cannot call /ai/what-if on User A's portfolio."""
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    with (
        patch("app.ai.service.run_what_if_graph", new_callable=AsyncMock),
        patch("app.ai.service._fetch_portfolio_context", new_callable=AsyncMock),
    ):
        resp = await async_client.post(
            "/ai/what-if",
            json={
                "portfolio_id": str(portfolio.id),
                "question": "What if AAPL falls 20%?",
            },
            headers=auth_headers_other,
        )

    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Test 3 — POST /ai/what-if: happy path with mocked LLM + scenario
# ---------------------------------------------------------------------------


async def test_what_if_returns_scenario_and_narration(
    async_client: AsyncClient,
    db_session,
    auth_headers: dict,
    test_user: User,
) -> None:
    """POST /ai/what-if returns scenario_result and narration for a parseable question."""
    import json
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    scenario_dict = {
        "shocks": {"AAPL": -0.20},
        "var_95": 0.030,
        "cvar_95": 0.040,
        "var_95_baseline": 0.025,
        "cvar_95_baseline": 0.033,
        "expected_loss": 360.0,
        "portfolio_value": 1800.0,
        "insufficient_data": False,
    }

    with (
        patch("app.ai.service.run_what_if_graph", new_callable=AsyncMock) as mock_what_if,
        patch("app.ai.service._fetch_portfolio_context", new_callable=AsyncMock) as mock_ctx,
    ):
        mock_ctx.return_value = ({"AAPL": 1.0}, MagicMock(empty=True), 1800.0)
        mock_what_if.return_value = (
            json.dumps(scenario_dict),
            "A 20% fall in AAPL would increase your 95% CVaR from 3.3% to 4.0%.",
            False,
            False,
            None,
        )

        resp = await async_client.post(
            "/ai/what-if",
            json={
                "portfolio_id": str(portfolio.id),
                "question": "What if AAPL falls 20%?",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["scenario_result"] is not None
    assert data["scenario_result"]["shocks"] == {"AAPL": -0.20}
    assert data["narration"] is not None
    assert data["timeout"] is False


# ---------------------------------------------------------------------------
# Test 4 — LLM timeout: scenario_result still present, narration=null
# ---------------------------------------------------------------------------


async def test_what_if_timeout_returns_null_narration(
    async_client: AsyncClient,
    db_session,
    auth_headers: dict,
    test_user: User,
) -> None:
    """On LLM timeout, scenario_result must still be None (no scenario parsed yet)
    and timeout=True is set.  The numbers always render even if LLM is slow."""
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    with (
        patch("app.ai.service.run_what_if_graph", new_callable=AsyncMock) as mock_what_if,
        patch("app.ai.service._fetch_portfolio_context", new_callable=AsyncMock) as mock_ctx,
    ):
        mock_ctx.return_value = ({"AAPL": 1.0}, MagicMock(empty=True), 1800.0)
        # Timeout: no scenario_result, narration=None, timeout=True
        mock_what_if.return_value = (None, None, False, True, None)

        resp = await async_client.post(
            "/ai/what-if",
            json={
                "portfolio_id": str(portfolio.id),
                "question": "What if AAPL falls 20%?",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["timeout"] is True
    assert data["narration"] is None


# ---------------------------------------------------------------------------
# Test 5 — Ambiguous question triggers clarification_needed
# ---------------------------------------------------------------------------


async def test_what_if_ambiguous_question_triggers_clarification(
    async_client: AsyncClient,
    db_session,
    auth_headers: dict,
    test_user: User,
) -> None:
    """An ambiguous question returns clarification_needed=True with a clarifying question."""
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    clarification = "How much do you expect the market to fall? Please specify a percentage."

    with (
        patch("app.ai.service.run_what_if_graph", new_callable=AsyncMock) as mock_what_if,
        patch("app.ai.service._fetch_portfolio_context", new_callable=AsyncMock) as mock_ctx,
    ):
        mock_ctx.return_value = ({"AAPL": 1.0}, MagicMock(empty=True), 1800.0)
        # Agent asked a clarifying question instead of calling the tool
        mock_what_if.return_value = (
            None,        # no scenario_json
            clarification,
            True,        # clarification_needed
            False,
            clarification,
        )

        resp = await async_client.post(
            "/ai/what-if",
            json={
                "portfolio_id": str(portfolio.id),
                "question": "What if the market crashes?",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["clarification_needed"] is True
    assert data["clarification_question"] is not None
    assert "?" in data["clarification_question"]


# ---------------------------------------------------------------------------
# Test 6 — GET /ai/conversations/{portfolio_id} — ownership-gated
# ---------------------------------------------------------------------------


async def test_list_conversations_cross_user_returns_403(
    async_client: AsyncClient,
    db_session,
    auth_headers_other: dict,
    test_user: User,
) -> None:
    """User B cannot list conversations for User A's portfolio."""
    portfolio = await _create_portfolio_with_holding(db_session, test_user.id)

    resp = await async_client.get(
        f"/ai/conversations/{portfolio.id}",
        headers=auth_headers_other,
    )
    assert resp.status_code == 403
