from __future__ import annotations

from abc import abstractmethod
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

import datetime
import asyncio
import logging

from ..data_source import BaseDataSource
from ..data_source import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property

class BaseWebApp(FastAPI):
    def __init__(self, datasource: BaseDataSource, title: str = "Frida Unity Inspector") -> None:
        self.datasource = datasource

        super().__init__(
            title=title,
            lifespan=self._lifespan
        )

        self._register_routes()

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"fui.web_app")

    def get_logger(self, subname: str | None = None) -> logging.Logger:
        return logging.getLogger(f"fui.web_app.{subname}" if subname else "fui.web_app")

    def _handle_log(self, log: LogEntry):
        human_timestamp = datetime.datetime.fromtimestamp(log.timestamp).strftime("%Y/%m/%d %H:%M:%S")
        log_message = f"[{human_timestamp}] [{log.id}] {log.message} {f" from {log.source}" if log.source else ""} {f"\n {log.stack_trace}" if log.stack_trace else ""}"

        if log.kind == "log":
            self.logger.info(log_message)
        elif log.kind == "warning":
            self.logger.warning(log_message)
        elif log.kind == "error":
            self.logger.error(log_message)
        else:
            self.logger.warning("Unknown log kind, defaulting to 'info'")
            self.logger.info(log_message)

    # -- lifecycle --
    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI):
        unsubscribe = self.datasource.subscribe(self._handle_log)
        self.datasource.start()
        try:
            yield
        finally:
            unsubscribe()
            self.datasource.stop()

    @abstractmethod
    def _register_routes(self) -> None:
        pass
