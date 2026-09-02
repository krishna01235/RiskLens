"""ws/router.py — WebSocket ticket issuance and handling."""

import secrets
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.auth.models import User
from app.database import get_db
from app.deps import get_current_user, get_redis
from app.portfolios.service import _get_portfolio_owned
from app.ws.connection_manager import manager

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.post("/ticket")
async def get_ws_ticket(
    user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
):
    """Issue a short-lived one-time ticket for a WebSocket connection."""
    ticket = secrets.token_hex(16)
    # Store ticket pointing to user_id for 60 seconds
    await redis.setex(f"ws_ticket:{ticket}", 60, str(user.id))
    return {"ticket": ticket}


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Handle incoming WebSocket connection."""
    # Ensure manager has redis reference for pubsub listener
    if manager.redis is None:
        manager.redis = redis

    # Validate ticket
    user_id_str = await redis.get(f"ws_ticket:{ticket}")
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Invalidate ticket so it can't be reused
    await redis.delete(f"ws_ticket:{ticket}")
    user_id = uuid.UUID(user_id_str)

    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe":
                portfolio_id_str = data.get("portfolio_id")
                if not portfolio_id_str:
                    continue
                
                try:
                    portfolio_id = uuid.UUID(portfolio_id_str)
                    # Verify ownership
                    await _get_portfolio_owned(db, portfolio_id, user_id)
                    # Subscribe
                    await manager.subscribe(websocket, str(portfolio_id))
                except Exception:
                    # Ignore invalid requests or unowned portfolios
                    pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
