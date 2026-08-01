from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("fui.utils.device_discovery")

# Map ADB transport state -> status name
_ADB_STATE_MAP = {
    "device":       "ONLINE",
    "offline":      "OFFLINE",
    "unauthorized": "ERROR",
    "recovery":     "ERROR",
    "sideload":     "BUSY",
}

_GETPROP_KEYS = {
    "model":       "ro.product.model",
    "brand":       "ro.product.brand",
    "android_ver": "ro.build.version.release",
    "sdk":         "ro.build.version.sdk",
}


@dataclass
class DiscoveredDevice:
    """A single device seen in `adb devices -l`, plus fetched metadata."""
    device_id: str
    adb_state: str
    status: str  # mapped from adb_state via _ADB_STATE_MAP, else "UNKNOWN"
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.meta.get("model") or self.device_id


async def discover_devices(
    adb_path: str = "adb",
    fetch_meta: bool = True,
    devices_timeout: float = 10.0,
    getprop_timeout: float = 5.0,
) -> list[DiscoveredDevice]:
    """
    Query ADB once and return the currently attached devices.

    :param adb_path: Path to the adb binary.
    :param fetch_meta: If True, also run `getprop` for model/brand/version/sdk
        on each device. The `adb devices -l` transport fields (product, model,
        device, transport_id) are always included under `_run_adb_devices_*` keys.
    :param devices_timeout: Timeout for the `adb devices -l` call.
    :param getprop_timeout: Per-property timeout for metadata fetches.
    :returns: A list of DiscoveredDevice (empty if adb failed or none attached).
    """
    raw = await _run_adb_devices(adb_path, timeout=devices_timeout)
    if raw is None:
        return []

    devices: list[DiscoveredDevice] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("List of"):
            continue
        parts = line.split()
        device_id = parts[0]
        adb_state = parts[1] if len(parts) > 1 else "unknown"

        meta: dict[str, Any] = {}
        for part in parts[2:]:
            if ":" in part:
                k, v = part.split(":", 1)
                meta[f"_run_adb_devices_{k}"] = v

        if fetch_meta:
            fetched = await _fetch_device_meta(adb_path, device_id, timeout=getprop_timeout)
            if fetched:
                meta.update(fetched)

        devices.append(
            DiscoveredDevice(
                device_id=device_id,
                adb_state=adb_state,
                status=_ADB_STATE_MAP.get(adb_state, "UNKNOWN"),
                meta=meta,
            )
        )
        logger.debug("Discovered device: %s (ADB state: %s)", device_id, adb_state)

    return devices


async def _run_adb_devices(adb_path: str, timeout: float = 10.0) -> Optional[str]:
    """Run `adb devices -l` and return its stdout, or None on failure."""
    try:
        proc = await asyncio.create_subprocess_exec(
            adb_path, "devices", "-l",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            logger.error("ADB command failed: %s", stderr.decode().strip())
            return None
        return stdout.decode(errors="replace")
    except FileNotFoundError as e:
        logger.error("ADB executable not found at path: %s - %s", adb_path, e)
        return None
    except asyncio.TimeoutError as e:
        logger.error("ADB command timed out after %.1f seconds - %s", timeout, e)
        return None
    except Exception as e:
        logger.error("Error running ADB command: %s", e, exc_info=True)
        return None


async def _fetch_device_meta(
    adb_path: str, device_id: str, timeout: float = 5.0
) -> Optional[dict[str, Any]]:
    """
    Fetch basic device metadata via `adb shell getprop`.

    Returns a dict of the props in _GETPROP_KEYS. A prop that times out is set
    to None rather than failing the whole fetch. Returns None only on a hard
    error (adb missing, unexpected exception).
    """
    meta: dict[str, Any] = {}
    for key, prop in _GETPROP_KEYS.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", device_id, "shell", "getprop", prop,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode == 0:
                meta[key] = stdout.decode().strip()
            else:
                logger.warning("Failed to get prop %s for device %s: %s", prop, device_id, stderr.decode().strip())
        except FileNotFoundError as e:
            logger.error("ADB executable not found at path: %s - %s", adb_path, e)
            return None
        except asyncio.TimeoutError as e:
            logger.error("ADB command for prop %s timed out after %.1f seconds for device %s - %s", prop, timeout, device_id, e)
            # Don't fail the whole metadata fetch if one prop times out; just skip it
            meta[key] = None
        except Exception as e:
            logger.error("Error running ADB command: %s", e, exc_info=True)
            return None

    return meta