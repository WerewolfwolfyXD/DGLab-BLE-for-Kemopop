import asyncio
import threading
import time

from .bluetooth import BleManager
from . import i18n


class DGLabV3Controller:
    """
    DG-LAB V3 蓝牙控制核心，负责维持心跳包和发送指令。
    """
    UUID_SERVICE = "0000180C-0000-1000-8000-00805f9b34fb"
    UUID_WRITE   = "0000150A-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        self.client = None
        self.loop = asyncio.new_event_loop()
        self.running = False

        self.target_freq = 0
        self.target_int_a = 0
        self.target_int_b = 0

        self.channel_a_active = True
        self.channel_b_active = True

        self.status_callback = None
        self.debug_callback = None

    def start_thread(self):
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._bt_lifecycle())

    async def _bt_lifecycle(self):
        self.running = True
        while self.running:
            try:
                if self.status_callback: self.status_callback(i18n.t("scanning_devices"))
                device = await BleManager.find_device_by_filter(
                    lambda d, ad: d.name and ("47L121" in d.name or "D-LAB" in d.name or "Coyote" in d.name)
                )

                if not device:
                    if self.status_callback: self.status_callback(i18n.t("device_not_found", seconds=3))
                    await asyncio.sleep(3)
                    continue

                if self.status_callback: self.status_callback(i18n.t("trying_connect", device=device.name))
                async with BleManager.Client(device) as client:
                    self.client = client

                    bf_packet = bytearray([0xBF, 0x64, 0x64, 0x00, 0x00, 0x00, 0x00])
                    await client.write_gatt_char(self.UUID_WRITE, bf_packet)
                    if self.debug_callback: self.debug_callback(i18n.t("bf_sent"))

                    if self.status_callback: self.status_callback(i18n.t("connected"))

                    # 循环发送心跳包 (V3要求每100ms发送一次)
                    while client.is_connected and self.running:
                        packet = self._build_packet()
                        await client.write_gatt_char(self.UUID_WRITE, packet)
                        if self.debug_callback and time.time() % 1.0 < 0.1:
                            self.debug_callback(f"[Heartbeat] Freq: {self.target_freq}Hz, Int A: {self.target_int_a}%, Int B: {self.target_int_b}%")

                        await asyncio.sleep(0.1)

            except Exception as e:
                err = str(e)
                if "NotConnectedError" not in err:
                    err = f"{e.__class__.__name__} ({err})"
                if self.status_callback: self.status_callback(i18n.t("bt_error", err=err))
                await asyncio.sleep(3)
            finally:
                self.client = None

    def _build_packet(self):
        """构建 V3 B0指令: 使用存储的 target_freq, target_int_a, target_int_b"""

        freq = max(1, min(100, int(self.target_freq)))
        val_a = max(0, min(100, int(self.target_int_a)))
        val_b = max(0, min(100, int(self.target_int_b)))

        parsing_method_and_seq = 0x0F
        max_channel_strength = 0x64

        packet = bytearray([0xB0, parsing_method_and_seq, max_channel_strength, max_channel_strength])

        if self.channel_a_active:
            packet.extend([freq] * 4)
            packet.extend([val_a] * 4)
        else:
            packet.extend([0] * 8)

        if self.channel_b_active:
            packet.extend([freq] * 4)
            packet.extend([val_b] * 4)
        else:
            packet.extend([0] * 8)

        return packet

    def set_shock_split_wave(self, freq, intensity_a, intensity_b):
        self.target_freq = freq
        self.target_int_a = intensity_a
        self.target_int_b = intensity_b

    def set_channels(self, a_active, b_active):
        self.channel_a_active = a_active
        self.channel_b_active = b_active
