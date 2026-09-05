"""app/slack/router.py — Slack account link/unlink endpoints.

Routes:
  POST /slack/link    — unauthenticated; Slack bot calls this to exchange a
                        one-time code for a linked API token.
  POST /slack/unlink  — JWT-authenticated; web dashboard action to revoke the
                        linked token and delete the SlackLink row.

Rate limiting:
  POST /slack/link    — 10/minute (the bot will call this exactly once per
                        /risklens login attempt; the limit prevents brute-force
                        code guessing).
  POST /slack/unlink  — 20/minute (generous; just a guard).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service as auth_service
from app.auth.models import User
from app.auth.schemas import SlackLinkRequest
from app.database import get_db
from app.deps import get_current_user, get_redis, limiter

slack_router = APIRouter(prefix="/slack", tags=["slack"])


# ── POST /slack/link ──────────────────────────────────────────────────────────


@slack_router.post("/link", status_code=200)
@limiter.limit("10/minute")
async def link_slack(
    body: SlackLinkRequest,
    request: Request,  # noqa: ARG001  # required by slowapi
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis=Depends(get_redis),  # noqa: B008
) -> dict[str, bool]:
    """Exchange a one-time code for a linked Slack account.

    Called by the Slack bot when a user runs ``/risklens login <code>``.
    This endpoint is intentionally **unauthenticated** — the one-time code
    was issued by an authenticated web-dashboard session, so it carries the
    identity implicitly.  The code is single-use and expires after
    ONE_TIME_CODE_TTL_SECONDS seconds, making brute-force impractical.

    On success, creates (or replaces) a ``slack_links`` row and caches the
    raw API token in Redis so the bot can retrieve it for subsequent calls.

    Returns ``{"linked": true}`` on success.
    404 if the code is missing, already used, or expired.
    """
    try:
        raw_token, api_token = await auth_service.exchange_one_time_code(
            db, redis, body.code, body.slack_user_id
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    # Cache the raw token keyed by token_id so get_linked_api_token_raw can
    # retrieve it. TTL is generous — revocation handles security, not expiry.
    await redis.set(f"rl:rawtoken:{api_token.id}", raw_token, ex=86400 * 30)  # 30 days

    return {"linked": True}


# ── POST /slack/unlink ────────────────────────────────────────────────────────


@slack_router.post("/unlink", status_code=200)
@limiter.limit("20/minute")
async def unlink_slack(
    body: SlackLinkRequest,
    request: Request,  # noqa: ARG001  # required by slowapi
    db: AsyncSession = Depends(get_db),  # noqa: B008
    redis=Depends(get_redis),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, bool]:
    """Revoke the linked API token and delete the Slack link.

    Called from the web dashboard by the authenticated user.
    403 if the link belongs to another user.
    404 if no link exists for the given slack_user_id.
    """
    try:
        await auth_service.unlink_slack_user(
            db, redis, current_user.id, body.slack_user_id
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {"linked": False}
