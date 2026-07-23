from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

import datetime
import asyncio
import logging

from typing_extensions import override

from ..base_app import BaseWebApp
from ..websocket_hub import WebSocketHub
from ...data_source import BaseDataSource
from ...data_source import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property

CURRENT_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = CURRENT_DIR / "public" # css/js
VIEWS_DIR = CURRENT_DIR / "views" # html


class UnityEditorWebApp(BaseWebApp):
    def __init__(self, datasource: BaseDataSource) -> None:
        self.hub = WebSocketHub()
        super().__init__(datasource, title="Frida Unity Inspector")

    @override
    async def _lifespan(self, _app: FastAPI):
        self.hub.bind_loop(asyncio.get_event_loop())
        super()._lifespan(_app)

    def _register_routes(self) -> None:
        # Web page
        self.add_api_route("/", self.index, methods=["GET"])

        # Web Socket
        self.add_api_websocket_route("/ws", self.ws_endpoint)

        # API
        self.add_api_route("/api/status", self.status, methods=["GET"])

        self.mount("/css", StaticFiles(directory=PUBLIC_DIR / "css"), name="css")
        self.mount("/js", StaticFiles(directory=PUBLIC_DIR / "js"), name="js")

    # -- pages ------
    async def index(self) -> FileResponse:
        return FileResponse(VIEWS_DIR / "index.html")

    # -- REST API ---
    async def status(self) -> dict:
        return self.datasource.status().model_dump()

    # TODO

    # -- WebSocket --
    async def ws_endpoint(self, ws: WebSocket) -> None:
        await self.hub.connect(ws)
        try:
            await ws.send_json(
                {"type": "status", "status": self.datasource.status().model_dump()}
            )
            for entry in self.datasource.get_log_history():
                await ws.send_json({"type": "log", "entry": entry.model_dump()})
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            self.hub.disconnect(ws)
        except Exception:
            self.hub.disconnect(ws)