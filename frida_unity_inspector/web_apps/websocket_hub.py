from __future__ import annotations

from fastapi import WebSocket
import asyncio
import logging

log = logging.getLogger("fui.WebSocketHub")

class WebSocketHub:
    """
    Handles data communication between clients and server in realtime.
    Used for:
    - Broadcast of log/events
        * Server broadcast any new logs to clients, who receive it and display it in the console
        * Some value has changed in the game. i.e. object moved. active changed etc. Send the new info to all clients to update.

    TODO - Others. This will be used also by the freecam for WASD/movement.
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, ws: WebSocket) -> None:
        log.trace(f"WebSocketHub: connect {ws.client}")
        await ws.accept()
        self._clients.add(ws)
        log.spam(f"WebSocketHub: connected {ws.client}, total clients: {len(self._clients)}")

    def disconnect(self, ws: WebSocket) -> None:
        log.trace(f"WebSocketHub: disconnect {ws.client}")
        self._clients.discard(ws)
        log.spam(f"WebSocketHub: disconnected {ws.client}, total clients: {len(self._clients)}")

    async def _send_all(self, payload: dict) -> None:
        log.trace(f"WebSocketHub: sending payload to {len(self._clients)} clients")
        dead = []
        for ws in list(self._clients):
            try:
                log.spam(f"WebSocketHub: sending payload to {ws.client}")
                log.god_save_you(f"WebSocketHub: payload: {payload}")
                await ws.send_json(payload)
                log.spam(f"WebSocketHub: sent payload to {ws.client}")
            except Exception:
                log.spam(f"WebSocketHub: failed to send payload to {ws.client}, marking as dead")
                dead.append(ws)
        log.trace(f"WebSocketHub: finished sending payload, disconnecting {len(dead)} dead clients")
        for ws in dead:
            self.disconnect(ws)

    def broadcast_threadsafe(self, payload: dict) -> None:
        """Thread-safe broadcast — callable from the Frida message pump."""
        log.trace(f"WebSocketHub: broadcasting payload to {len(self._clients)} clients")
        if self._loop is None:
            log.error("WebSocketHub: event loop not bound, cannot broadcast")
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(self._send_all(payload))
        )
        log.spam(f"WebSocketHub: broadcast scheduled for {len(self._clients)} clients")
