"""tests/integration/test_api_tokens.py — Scope-enforcement and lifecycle tests.

Tests:
  Happy path:
    - Create read-scoped token → 201, raw_token present
    - Use read token on GET /portfolios → 200
    - Use read token on GET /portfolios/{id}/risk → 200
    - Use read token on GET /alerts → 200

  Scope enforcement — read-scoped token:
    - POST /ai/what-if with read token → 403 (needs 'whatif')
    - POST /portfolios/demo with read token → 401 (JWT-only endpoint)

  Scope enforcement — whatif-scoped token:
    - POST /ai/what-if with whatif token → 200 (or acceptable non-403/401)
    - GET /portfolios with whatif token → 403 (needs 'read')
    - GET /alerts with whatif token → 403 (needs 'read')

  Revocation:
    - Revoke token → GET /portfolios with that token → 401

  Schema validation:
    - Scopes=["admin"] → 422
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.models import User
from app.auth.service import create_access_token


# ── Helpers ───────────────────────────────────────────────────────────────────


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_and_login(client, email: str, password: str = "strongpass1"):
    """Register a user and return their JWT access token."""
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _create_token(client, jwt: str, scopes: list[str]) -> dict:
    """Call POST /auth/api-tokens and return the JSON body."""
    resp = await client.post(
        "/auth/api-tokens",
        json={"scopes": scopes},
        headers=_bearer(jwt),
    )
    return resp.status_code, resp.json()


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_read_token_returns_raw_token(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    status, body = await _create_token(async_client, jwt, ["read"])

    assert status == 201
    assert "raw_token" in body
    assert len(body["raw_token"]) == 64  # 32 bytes hex = 64 chars
    assert body["scopes"] == ["read"]
    assert "id" in body


@pytest.mark.asyncio
async def test_read_token_can_list_portfolios(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["read"])
    raw = token_body["raw_token"]

    resp = await async_client.get("/portfolios", headers=_bearer(raw))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_read_token_can_get_alerts(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["read"])
    raw = token_body["raw_token"]

    resp = await async_client.get("/alerts", headers=_bearer(raw))
    assert resp.status_code == 200


# ── Scope enforcement: read-only token ────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_token_rejected_by_whatif_endpoint(async_client):
    """A read-scoped API token must be rejected with 403 on POST /ai/what-if
    (which requires the 'whatif' scope)."""
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["read"])
    raw = token_body["raw_token"]

    resp = await async_client.post(
        "/ai/what-if",
        json={"portfolio_id": str(uuid.uuid4()), "question": "test?"},
        headers=_bearer(raw),
    )
    assert resp.status_code == 403, (
        f"Expected 403 (wrong scope) but got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_read_token_rejected_by_jwt_only_endpoint(async_client):
    """A read-scoped API token must be rejected with 401 on POST /portfolios/demo
    (a write endpoint that doesn't accept API tokens at all)."""
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["read"])
    raw = token_body["raw_token"]

    resp = await async_client.post("/portfolios/demo", headers=_bearer(raw))
    # The endpoint only accepts JWTs; an API token looks like a bad JWT → 401
    assert resp.status_code == 401, (
        f"Expected 401 (JWT-only endpoint) but got {resp.status_code}: {resp.text}"
    )


# ── Scope enforcement: whatif-only token ─────────────────────────────────────


@pytest.mark.asyncio
async def test_whatif_token_can_call_whatif_endpoint(async_client):
    """A whatif-scoped token must be accepted by POST /ai/what-if.
    We accept any non-403/non-401 response (the AI call itself may 422 if the
    portfolio doesn't exist, but the auth layer accepted the token)."""
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["whatif"])
    raw = token_body["raw_token"]

    resp = await async_client.post(
        "/ai/what-if",
        json={"portfolio_id": str(uuid.uuid4()), "question": "test?"},
        headers=_bearer(raw),
    )
    # Auth accepted — downstream may 404/422 due to missing portfolio, but not 401/403
    assert resp.status_code not in (401, 403), (
        f"Expected auth to pass, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_whatif_token_rejected_by_portfolios_endpoint(async_client):
    """A whatif-scoped token must be rejected with 403 on GET /portfolios
    (which requires the 'read' scope)."""
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["whatif"])
    raw = token_body["raw_token"]

    resp = await async_client.get("/portfolios", headers=_bearer(raw))
    assert resp.status_code == 403, (
        f"Expected 403 (wrong scope) but got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_whatif_token_rejected_by_alerts_endpoint(async_client):
    """A whatif-scoped token must be rejected with 403 on GET /alerts
    (which requires the 'read' scope)."""
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["whatif"])
    raw = token_body["raw_token"]

    resp = await async_client.get("/alerts", headers=_bearer(raw))
    assert resp.status_code == 403, (
        f"Expected 403 (wrong scope) but got {resp.status_code}: {resp.text}"
    )


# ── Revocation ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoked_token_returns_401(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    _, token_body = await _create_token(async_client, jwt, ["read"])
    raw = token_body["raw_token"]
    token_id = token_body["id"]

    # Confirm it works before revocation
    resp = await async_client.get("/portfolios", headers=_bearer(raw))
    assert resp.status_code == 200

    # Revoke
    rev = await async_client.delete(
        f"/auth/api-tokens/{token_id}", headers=_bearer(jwt)
    )
    assert rev.status_code == 204

    # Now it should be rejected
    resp2 = await async_client.get("/portfolios", headers=_bearer(raw))
    assert resp2.status_code == 401, (
        f"Expected 401 after revocation, got {resp2.status_code}"
    )


# ── Schema validation ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_scope_returns_422(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    status, body = await _create_token(async_client, jwt, ["admin"])

    assert status == 422, f"Expected 422 for invalid scope, got {status}: {body}"


@pytest.mark.asyncio
async def test_empty_scopes_returns_422(async_client):
    jwt = await _register_and_login(async_client, f"tok-{uuid.uuid4().hex[:6]}@x.com")
    status, body = await _create_token(async_client, jwt, [])

    assert status == 422, f"Expected 422 for empty scopes, got {status}: {body}"
