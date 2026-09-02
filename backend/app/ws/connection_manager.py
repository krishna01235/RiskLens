"""ws/connection_manager.py — WebSocket connection state and fan-out."""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # websocket -> set of portfolio_ids
        self.active_connections: Dict[WebSocket, Set[str]] = defaultdict(set)
        # portfolio_id -> set of websockets
        self.portfolio_subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)
        # portfolio_id -> asyncio.Task (pubsub listener)
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}
        # Keep track of redis instance
        self.redis: Redis | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        portfolio_ids = self.active_connections.pop(websocket, set())
        for pid in portfolio_ids:
            if pid in self.portfolio_subscriptions:
                self.portfolio_subscriptions[pid].discard(websocket)
                # If no more connections for this portfolio, cancel the pubsub listener
                if not self.portfolio_subscriptions[pid]:
                    self.portfolio_subscriptions.pop(pid, None)
                    task = self.pubsub_tasks.pop(pid, None)
                    if task:
                        task.cancel()

    async def subscribe(self, websocket: WebSocket, portfolio_id: str):
        self.active_connections[websocket].add(portfolio_id)
        self.portfolio_subscriptions[portfolio_id].add(websocket)
        
        # Start pubsub listener if not already running for this portfolio
        if portfolio_id not in self.pubsub_tasks:
            task = asyncio.create_task(self._listen_to_portfolio(portfolio_id))
            self.pubsub_tasks[portfolio_id] = task

    async def _listen_to_portfolio(self, portfolio_id: str):
        if not self.redis:
            logger.error("Redis not set on ConnectionManager")
            return
            
        pubsub = self.redis.pubsub()
        channel = f"risk_updates:{portfolio_id}"
        await pubsub.subscribe(channel)
        logger.info(f"Subscribed to {channel}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    # Forward to all connected websockets
                    websockets = self.portfolio_subscriptions.get(portfolio_id, set())
                    # Use a copy to avoid modified-during-iteration issues
                    for ws in list(websockets):
                        try:
                            await ws.send_text(data)
                        except Exception as e:
                            logger.error(f"Error sending message to ws: {e}")
        except asyncio.CancelledError:
            logger.info(f"Stopped listening to {channel}")
        except Exception as e:
            logger.error(f"Pubsub listener error on {channel}: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

manager = ConnectionManager()
