from __future__ import annotations

import logging

import frida

from frida_unity_inspector.utils import DiscoveredDevice, discover_devices

logger = logging.getLogger("fui.frida.device_resolver")


async def resolve_frida_device(choice: str) -> frida.core.Device:
    """
    :param choice: "local" for this PC, "adb" to discover devices via ADB (prompting if more than one), or an explicit frida device id.
    :raises RuntimeError: if "adb" is specified but no devices are found.
    """
    if choice == "local":
        logger.info("Using local device")
        return frida.get_local_device()
    if choice == "adb":
        logger.info("Using ADB device discovery")
        return await _resolve_adb_device()
    logger.info(f"Using device: {choice}")
    return frida.get_device(choice)


async def _resolve_adb_device() -> frida.core.Device:
    devices = await discover_devices()
    if not devices:
        raise RuntimeError("No devices found via ADB. Please ensure ADB is installed and the device is connected.")
    if len(devices) == 1:
        device = frida.get_device(devices[0].device_id)
        logger.info(f"Selected 1st due to only 1 device found: {device} (ADB state: {devices[0].adb_state})")
        return device
    return _prompt_device_choice(devices)


def _prompt_device_choice(devices: list[DiscoveredDevice]) -> frida.core.Device:
    while True:
        logger.info(f"Multiple devices found. Please specify a device. Available devices: ")
        for i, d in enumerate(devices):
            logger.info(f"{i + 1}. {d.device_id} (ADB state: {d.adb_state})")
        choice = input(f">> ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(devices):
                device = frida.get_device(devices[choice_index].device_id)
                logger.info(f"Using device: {device} (ADB state: {devices[choice_index].adb_state})")
                return device
            else:
                logger.warning(f"Invalid selection. Please choose a number between 1 and {len(devices)}.")
        except ValueError:
            logger.warning("Invalid input. Please enter a number.")
