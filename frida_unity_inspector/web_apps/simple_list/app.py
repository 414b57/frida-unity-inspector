from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

import datetime
import asyncio
import logging

from typing import Any

from pydantic import BaseModel
from typing_extensions import override

from ..base_app import BaseWebApp
from ..websocket_hub import WebSocketHub
from ...data_source import BaseDataSource, DataUpdate
from ...data_source import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, BaseProperty ,Property

INDEX_FILE = Path(__file__).resolve().parent / "index.html"


# -- request bodies --
class SetActiveRequest(BaseModel):
    object_id: str
    active: bool


class SetComponentEnabledRequest(BaseModel):
    object_id: str
    component_id: str
    enabled: bool


class SetPropertyRequest(BaseModel):
    object_id: str
    component_id: str
    property: Property


class SimpleListWebApp(BaseWebApp):
    def __init__(self, datasource: BaseDataSource) -> None:
        self._hub = WebSocketHub()
        super().__init__(datasource, title="Frida Unity Inspector - Simple List")
        # Push datasource updates (structure/property changes) to all connected pages.
        datasource.subscribe_updates(self._on_update)

    def _on_update(self, update: DataUpdate) -> None:
        self._hub.broadcast_threadsafe(update.model_dump(mode="json"))

    def _register_routes(self) -> None:
        # Web page
        self.add_api_route("/", self.index, methods=["GET"])

        # Realtime updates
        self.add_api_websocket_route("/ws", self.updates_ws)

        # API
        self.add_api_route("/api/status", self.status, methods=["GET"])
        self.add_api_route("/api/game_context", self.game_context, methods=["GET"])
        self.add_api_route("/api/scenes", self.scenes, methods=["GET"])
        self.add_api_route("/api/current_scene", self.current_scene, methods=["GET"])

        self.add_api_route("/api/set_active", self.set_active, methods=["POST"])
        self.add_api_route("/api/set_component_enabled", self.set_component_enabled, methods=["POST"])
        self.add_api_route("/api/set_property", self.set_property, methods=["POST"])

    # -- pages ------
    async def index(self) -> FileResponse:
        return FileResponse(INDEX_FILE,)

    # -- realtime ---
    async def updates_ws(self, websocket: WebSocket) -> None:
        self._hub.bind_loop(asyncio.get_running_loop())
        await self._hub.connect(websocket)
        try:
            while True:
                # Server-push only; drain (and ignore) anything the client sends.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            self._hub.disconnect(websocket)

    # -- REST API ---
    # - Read -
    async def status(self) -> dict:
        return (await self.datasource.status()).model_dump()

    async def game_context(self) -> dict:
        return (await self.datasource.get_game_context()).model_dump()

    async def scenes(self) -> list[dict]:
        return [scene.model_dump() for scene in await self.datasource.get_scenes()]

    async def current_scene(self) -> dict:
        return (await self.datasource.get_current_scene()).model_dump()

    # - Write -
    async def set_active(self, request: SetActiveRequest) -> dict:
        try:
            await self.datasource.set_active(request.object_id, request.active)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"ok": True}

    async def set_component_enabled(self, request: SetComponentEnabledRequest) -> dict:
        try:
            await self.datasource.set_component_enabled(request.object_id, request.component_id, request.enabled)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    async def set_property(self, request: SetPropertyRequest) -> dict:
        try:
            updated = await self.datasource.set_property(request.object_id, request.component_id, request.property)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if updated == None:
            raise HTTPException(status_code=400, detail="Property not found or not writable.")

        return {"ok": True, "property": updated.model_dump()}

