"""Bluetooth abstraction layer.
Provides a thin wrapper around bleak so higher-level code can import this module.
"""
from bleak import BleakScanner, BleakClient


class BleManager:
    """Simple adapter exposing the APIs used by the controller.
    This keeps direct bleak imports out of controller logic and makes testing easier.
    """
    @staticmethod
    async def find_device_by_filter(filter_fn):
        return await BleakScanner.find_device_by_filter(filter_fn)

    # Expose BleakClient for use as context manager
    Client = BleakClient


__all__ = ["BleManager"]
