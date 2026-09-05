"""slack_bot/app.py — Slack Bolt socket-mode application.

Commands:
  /risklens login <code>         — Exchange a web-dashboard one-time code to
                                   link this Slack account.
  /risklens status               — Show the risk snapshot for the user's
                                   primary portfolio.
  /risklens whatif <symbol> <pct>— Run a what-if scenario (e.g. AAPL -10).
  /risklens alerts               — Show recent risk alerts.

Run with:
  python -m slack_bot.app

Requires environment variables:
  SLACK_BOT_TOKEN   — xoxb-... bot OAuth token
  SLACK_APP_TOKEN   — xapp-... socket-mode app-level token
  RISKLENS_API_URL  — base URL of the RiskLens API (default: http://localhost:8000)
  DATABASE_URL      — async SQLAlchemy connection string (for SlackLink lookups)
  REDIS_URL         — Redis connection URL (for raw-token cache)
"""

from __future__ import annotations

import asyncio
import os

import httpx
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from slack_bot import api_client, formatters
from app.auth import service as auth_service

# ── Database session factory (read-only SlackLink lookups) ────────────────────

_engine = create_async_engine(
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://risklens:risklens@localhost:5432/risklens",
    ),
    pool_pre_ping=True,
)
_async_session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

# ── Redis connection for raw-token cache ──────────────────────────────────────

import redis.asyncio as _redis_lib

_redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_pool = _redis_lib.ConnectionPool.from_url(_redis_url, decode_responses=True)


async def _get_redis() -> _redis_lib.Redis:  # type: ignore[type-arg]
    return _redis_lib.Redis.from_pool(_redis_pool)


# ── Raw-token lookup ──────────────────────────────────────────────────────────


async def _get_raw_token(slack_user_id: str) -> str | None:
    """Return the cached raw API token for a linked Slack user, or None."""
    async with _async_session() as db:
        redis = await _get_redis()
        try:
            return await auth_service.get_linked_api_token_raw(db, redis, slack_user_id)
        finally:
            await redis.aclose()


# ── Slack Bolt app ─────────────────────────────────────────────────────────────

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])


async def _ack_and_run(ack, body, respond, handler):  # type: ignore[no-untyped-def]
    """Acknowledge immediately (Slack requires <3s) then run the async handler."""
    await ack()
    await handler(body, respond)


# ── /risklens login <code> ────────────────────────────────────────────────────


@app.command("/risklens")
async def handle_risklens(ack, body, respond):  # type: ignore[no-untyped-def]
    await ack()
    text: str = (body.get("text") or "").strip()
    slack_user_id: str = body["user_id"]

    parts = text.split()
    if not parts:
        await respond(
            "Usage: `/risklens <status|whatif <symbol> <pct>|alerts|login <code>>`"
        )
        return

    subcommand = parts[0].lower()

    # ── login ──────────────────────────────────────────────────────────────────
    if subcommand == "login":
        if len(parts) < 2:
            await respond(
                ":lock: Please provide the one-time code from the RiskLens dashboard:\n"
                "`/risklens login <code>`"
            )
            return
        code = parts[1]
        try:
            linked = await api_client.exchange_code(code, slack_user_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                await respond(
                    ":x: Code not found, already used, or expired. "
                    "Generate a new one from the RiskLens dashboard."
                )
            else:
                await respond(f":x: Link failed ({exc.response.status_code}).")
            return
        if linked:
            await respond(
                ":white_check_mark: *Linked!* Your Slack account is now connected to RiskLens.\n"
                "Try `/risklens status` to see your portfolio risk."
            )
        return

    # ── All other subcommands require a linked account ─────────────────────────
    raw_token = await _get_raw_token(slack_user_id)
    if raw_token is None:
        await respond(blocks=formatters.format_not_linked())
        return

    # ── status ─────────────────────────────────────────────────────────────────
    if subcommand == "status":
        try:
            portfolios = await api_client.get_portfolios(raw_token)
            if not portfolios:
                await respond(":warning: No portfolios found on your account.")
                return
            risk = await api_client.get_risk(raw_token, portfolios[0]["id"])
            blocks = formatters.format_risk_status(portfolios, risk)
            await respond(blocks=blocks)
        except httpx.HTTPStatusError as exc:
            await respond(f":x: API error ({exc.response.status_code}). Please try again.")
        return

    # ── whatif <symbol> <pct> ──────────────────────────────────────────────────
    if subcommand == "whatif":
        if len(parts) < 3:
            await respond("Usage: `/risklens whatif AAPL -10`  (symbol and % shock)")
            return
        symbol = parts[1].upper()
        pct = parts[2]
        try:
            portfolios = await api_client.get_portfolios(raw_token)
            if not portfolios:
                await respond(":warning: No portfolios found on your account.")
                return
            question = f"What happens to my portfolio if {symbol} moves {pct}%?"
            response = await api_client.post_what_if(
                raw_token, portfolios[0]["id"], question
            )
            blocks = formatters.format_whatif(response)
            await respond(blocks=blocks)
        except httpx.HTTPStatusError as exc:
            await respond(f":x: API error ({exc.response.status_code}). Please try again.")
        return

    # ── alerts ─────────────────────────────────────────────────────────────────
    if subcommand == "alerts":
        try:
            alerts = await api_client.get_alerts(raw_token)
            blocks = formatters.format_alerts(alerts)
            await respond(blocks=blocks)
        except httpx.HTTPStatusError as exc:
            await respond(f":x: API error ({exc.response.status_code}). Please try again.")
        return

    # ── unknown subcommand ─────────────────────────────────────────────────────
    await respond(
        "Unknown subcommand. Usage:\n"
        "• `/risklens login <code>`\n"
        "• `/risklens status`\n"
        "• `/risklens whatif <symbol> <pct>`\n"
        "• `/risklens alerts`"
    )


# ── Entry point ───────────────────────────────────────────────────────────────


async def _main() -> None:
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(_main())
