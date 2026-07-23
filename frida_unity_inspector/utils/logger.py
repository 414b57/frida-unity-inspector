from __future__ import annotations

import asyncio
import datetime
import logging
import sys
from typing import Any

import colorama
colorama.init(autoreset=True)

# Custom sub-DEBUG Levels (lower than DEBUG (10), lower number = more verbose)
VERBOSE = 9
TRACE = 7
SPAM = 5
GOD_SAVE_YOU = 1

def install_custom_log_levels() -> None:
    logging.addLevelName(VERBOSE, "VERBOSE")
    logging.addLevelName(TRACE, "TRACE")
    logging.addLevelName(SPAM, "SPAM")
    logging.addLevelName(GOD_SAVE_YOU, "GOD_SAVE_YOU")

    orig_addLevelName = logging.addLevelName
    def addLevelName(level: int, levelName: str) -> None:
        """
        Hacky override of logging.addLevelName to prevent overwriting our custom levels.
        See `uvicorn.config.configure_logging` for why this is done. (sets our 5/spam text to trace)
        ```
        def configure_logging(self) -> None:
            logging.addLevelName(TRACE_LOG_LEVEL, "TRACE")
        ```
        """
        if level in (VERBOSE, TRACE, SPAM, GOD_SAVE_YOU):
            # Prevent overwriting our custom levels - See `uvicorn.config.configure_logging` which sets our 5/spam text to trace.
            return
        orig_addLevelName(level, levelName)
    logging.addLevelName = addLevelName  # type: ignore[assignment]

    def _verbose(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, message, args, stacklevel=2, **kwargs)

    def _trace(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, stacklevel=2, **kwargs)

    def _spam(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(SPAM):
            self._log(SPAM, message, args, stacklevel=2, **kwargs)

    def _god_save_you(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(GOD_SAVE_YOU):
            self._log(GOD_SAVE_YOU, message, args, stacklevel=2, **kwargs)

    logging.Logger.verbose = _verbose  # type: ignore[attr-defined]
    logging.Logger.trace = _trace  # type: ignore[attr-defined]
    logging.Logger.spam = _spam  # type: ignore[attr-defined]
    logging.Logger.god_save_you = _god_save_you  # type: ignore[attr-defined]

# Colour Maps
LEVEL_COLOURS: dict[int, str] = {
    logging.CRITICAL: "\033[1;97;41m",  # bold white on red background
    logging.ERROR:    "\033[91m",       # bright red
    logging.WARNING:  "\033[93m",       # bright yellow
    logging.INFO:     "\033[96m",       # bright cyan
    logging.DEBUG:    "\033[90m",       # gray

    VERBOSE:          "\033[94m",       # bright blue
    TRACE:            "\033[95m",       # bright magenta
    SPAM:             "\033[92m",       # bright green
    GOD_SAVE_YOU:     "\033[97;45m",    # white on magenta background
}
RESET = "\033[0m"

class FrameworkFormatter(logging.Formatter):
    """
    Compact, readable log formatter.

    Format/:
        HH:MM:SS.mmm  LEVEL  logger.name   message
    """

    def __init__(self, colorize: bool = True) -> None:
        super().__init__()
        self._colorize = colorize

    def format(self, record: logging.LogRecord) -> str:
        ts  = self.formatTime(record, "%H:%M:%S")
        ms  = f"{record.msecs:03.0f}"
        lvl = record.levelname.ljust(8)
        name = record.name[-25:].ljust(25)

        if self._colorize:
            col  = LEVEL_COLOURS.get(record.levelno, "")
            lvl  = f"{col}{lvl}{RESET}"

        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return f"{ts}.{ms}  {lvl}  {name}  {msg}"

class WebSocketLogHandler(logging.Handler):
    """
    Tees log records to an async queue so the dashboard can stream them.

    Usage:
        handler = WebSocketLogHandler()
        logging.getLogger("fui").addHandler(handler)
        # then drain handler.queue from an async task
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        super().__init__()
        self.log_counter = -1
        self._max_queue_size = max_queue_size
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue_size)

    def emit(self, record: logging.LogRecord) -> None:
        self.log_counter += 1
        try:
            log_entry = {
                "counter": self.log_counter,
                "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
                "logger": record.name,
                "level": record.levelname,
                "message": self.format(record)
            }
            try:
                self.queue.put_nowait(log_entry)
            except asyncio.QueueFull: # Drop oldest log to make room for new one
                self.queue.get_nowait()
                self.queue.put_nowait(log_entry)
        except Exception:
            self.handleError(record)


LEVEL_MAP: dict[str, int] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "verbose": VERBOSE,
    "trace": TRACE,
    "spam": SPAM,
    "god_save_you": GOD_SAVE_YOU,
    "gsy": GOD_SAVE_YOU,  # alias
}

def setup_logging(
    level: str = "INFO",
    colorize: bool = True,
    root_level: str = "GOD_SAVE_YOU",
    ws_level: str = "DEBUG",
    ws_max_queue_size: int = 1000,
) -> WebSocketLogHandler:
    """
    Configure root logger with console and websocket handlers.

    Returns the WebSocketLogHandler instance so the caller can drain its queue.
    """
    install_custom_log_levels()

    root_numeric_level = LEVEL_MAP.get(root_level.lower(), None)
    if root_numeric_level is None:
        raise ValueError(f"Invalid root log level: {root_level!r}")
    ws_numeric_level = LEVEL_MAP.get(ws_level.lower(), None)
    if ws_numeric_level is None:
        raise ValueError(f"Invalid websocket log level: {ws_level!r}")
    numeric_level = LEVEL_MAP.get(level.lower(), None)
    if numeric_level is None:
        raise ValueError(f"Invalid log level: {level!r}")

    root = logging.getLogger()
    # root.setLevel(GOD_SAVE_YOU)  # capture all logs, handlers will filter by level
    root.setLevel(root_numeric_level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    # console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setLevel(numeric_level)
    console.setFormatter(FrameworkFormatter(colorize=colorize and sys.stdout.isatty()))

    # WS handler (captures all framework logs for dashboard)
    ws_handler = WebSocketLogHandler(max_queue_size=ws_max_queue_size)
    ws_handler.setLevel(ws_numeric_level)

    fw_logger = logging.getLogger("fui")
    fw_logger.addHandler(console)
    fw_logger.addHandler(ws_handler)
    fw_logger.propagate = False

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    return ws_handler

log = logging.getLogger("fw.c.logger")

