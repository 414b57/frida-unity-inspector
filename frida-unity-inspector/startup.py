from __future__ import annotations

from dotenv import load_dotenv
import argparse
import os
import asyncio
import logging

from utils.logger import setup_logging, LEVEL_MAP

from data_source import BaseDataSource, MockDataSource#, FridaData

log = logging.getLogger("fui.startup")

# -- Args --
def parse_bool(val: str | None) -> bool:
    return val.strip().lower() in ("1", "true", "yes", "on", "enable", "enabled", "t", "y", "e", "active") if val is not None else False

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Frida Unity Inspector web app")

    logging_parent_group = p.add_argument_group(title="Logging")
    exclusive_logging = logging_parent_group.add_mutually_exclusive_group()
    exclusive_logging.add_argument("--debug", action="store_const", dest="log_level", const="DEBUG", default=argparse.SUPPRESS, help="enable debug logging")
    exclusive_logging.add_argument("--verbose", action="store_const", dest="log_level", const="VERBOSE", default=argparse.SUPPRESS, help="enable verbose logging")
    exclusive_logging.add_argument("--trace", action="store_const", dest="log_level", const="TRACE", default=argparse.SUPPRESS, help="enable trace logging")
    exclusive_logging.add_argument("--spam", action="store_const", dest="log_level", const="SPAM", default=argparse.SUPPRESS, help="enable spam logging")
    exclusive_logging.add_argument("--god-save-you", action="store_const", dest="log_level", const="GOD_SAVE_YOU", default=argparse.SUPPRESS, help="enable god-save-you logging")
    exclusive_logging.add_argument("--log-level",
                                choices=LEVEL_MAP.keys(),
                                default=os.environ.get("FUI_LOG_LEVEL", "INFO"),
                                help="set log level")

    data_parent_group = p.add_argument_group(title="Data Source")
    data_exclusive_group = data_parent_group.add_mutually_exclusive_group()
    data_exclusive_group.add_argument("--mock", action="store_const", dest="data_source", const="mock", default=argparse.SUPPRESS, help="Use `mock` data source")
    data_exclusive_group.add_argument("--frida", action="store_const", dest="data_source", const="mock", default=argparse.SUPPRESS, help="Use `frida` data source")
    data_exclusive_group.add_argument("--data_source",
                                    choices=["mock", "frida"],
                                    default=os.environ.get("FUI_DATA_SOURCE", "frida"),
                                    help="Define where data is gathered from, `mock` for test data | `frida` for real data")

    device_group = p.add_argument_group(title="Device")
    device_group.add_argument("--device", default=os.environ.get("FUI_DEVICE", "local"), help="frida device: local | usb | <device-id> (default: %(default)s)")
    device_group.add_argument("--package", default=os.environ.get("FUI_PACKAGE"), help="package to attach to")
    device_group.add_argument("--spawn", action="store_true", default=parse_bool(os.environ.get("FUI_SPAWN", "false")), help="spawn the target instead of attaching to a running one")

    hosting_group = p.add_argument_group(title="Web Hosting")
    hosting_group.add_argument("--host", default=os.environ.get("FUI_HOST", "127.0.0.1"), help="Address to bind the web server to (default: %(default)s)")
    hosting_group.add_argument("--port", type=int, default=int(os.environ.get("FUI_PORT", "8000")), help="Port to bind the web server to (default: %(default)s)")

    return p.parse_args()

# -- Run --
def build_data_source(data_source: str) -> BaseDataSource:
    if data_source == "frida":
        raise NotImplementedError("Frida data sources not yet implemented")
    elif data_source == "mock":
        return MockDataSource()

    raise ValueError(f"Unknown Data source specified - {data_source}")

def main():
    load_dotenv()
    args = parse_args()

    log_level = args.log_level
    setup_logging(level=log_level)

    data_source_type = args.data_source

    log.info(f"Starting Frida Unity Inspector at log level: {log_level} with data source: {data_source_type}")
    if data_source_type == "mock":
        log.warning("NOTICE: Using mock data source, this data is FAKE. And mainly used for testing frontend and backend integration and usability.")

    data_source = build_data_source(data_source_type)
    log.info(f"Data source {data_source_type} initialized: {data_source}")

if __name__ == "__main__":
    main()
