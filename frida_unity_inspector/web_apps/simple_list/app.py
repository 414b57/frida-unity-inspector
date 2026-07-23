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
from ...data_source import BaseDataSource, MockDataSource#, FridaData
from ...data_source import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property

INDEX_FILE = Path(__file__).resolve().parent / "index.html"


class SimpleListWebApp(BaseWebApp):
    def __init__(self, datasource: BaseDataSource) -> None:
        super().__init__(datasource, title="Frida Unity Inspector - Simple List")

    def _register_routes(self) -> None:
        # Web page
        self.add_api_route("/", self.index, methods=["GET"])

        # API
        self.add_api_route("/api/status", self.status, methods=["GET"])

    # -- pages ------
    async def index(self) -> FileResponse:
        return FileResponse(INDEX_FILE,)

    # -- REST API ---
    async def status(self) -> dict:
        return self.datasource.status().model_dump()

