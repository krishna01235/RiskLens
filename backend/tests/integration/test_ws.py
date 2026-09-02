"""tests/test_ws.py — Integration tests for WebSocket routing."""

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
import uuid
import json
from fastapi.testclient import TestClient

# We use the synchronous TestClient for WebSockets since httpx doesn't fully support WS yet
# in the standard way for Starlette, or we use Starlette's TestClient
from app.main import app

@pytest.mark.asyncio
async def test_ws_ticket_issuance_and_connection(
    async_client: AsyncClient,
    logged_in_headers: dict[str, str],
    redis: Redis,
    user_id: uuid.UUID
):
    # 1. Issue ticket
    resp = await async_client.post("/ws/ticket", headers=logged_in_headers)
    assert resp.status_code == 200
    ticket = resp.json()["ticket"]
    
    # 2. Check redis for ticket
    stored_user_id = await redis.get(f"ws_ticket:{ticket}")
    assert stored_user_id == str(user_id)
    
    # 3. Connect via WebSocket using TestClient
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
            # Ticket should be deleted after connection
            pass
            
    # Verify ticket deleted
    deleted_user_id = await redis.get(f"ws_ticket:{ticket}")
    assert deleted_user_id is None
