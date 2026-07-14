import asyncio
import json
from typing import List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[ws] Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[ws] Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all active WebSocket clients concurrently.

        Previously this looped sequentially with `await send_text()` — a slow
        or stalled client blocked every subsequent send, adding latency
        proportional to the number of connected clients.

        Now we:
        1. Snapshot `active_connections` so mutations during the gather don't
           cause iteration errors.
        2. Fan-out with `asyncio.gather(..., return_exceptions=True)` so all
           sends are concurrent and one failure never aborts the others.
        3. Prune connections that raised exceptions after the gather completes.
        """
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)

        # Snapshot to avoid mutation during async yields
        connections = list(self.active_connections)

        results = await asyncio.gather(
            *[conn.send_text(payload) for conn in connections],
            return_exceptions=True,
        )

        # Prune stale connections identified by exceptions
        for conn, result in zip(connections, results):
            if isinstance(result, Exception):
                print(f"[ws-err] Failed to send to client ({type(result).__name__}): {result}")
                self.disconnect(conn)


ws_manager = ConnectionManager()
