import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import queue
import asyncio
import re
import time
import sys
import os
import json
import math
from bleak import BleakScanner, BleakClient

# ==========================================
# DG-LAB V3 Hex 波形数据 (来自 https://github.com/BobH233/DGLab-v2-PulseData)
# ==========================================
USER_HEX_WAVEFORMS = {
    "渐变弹跳": [
        "210100", "210103", "418106", "61010A", "610100", "810103", "A18106", "C1010A", "C10100", "C10103",
        "C28106", "E2010A", "E20100", "020203", "228206", "42020A", "420200", "420203", "628206", "82020A",
        "820200", "A20203", "C28206", "E2020A", "E20200", "E20203", "028306", "22030A", "220300", "420303",
        "628306", "82030A", "820300", "820303", "A28306", "C2030A", "C20300", "E20303", "028406", "22040A",
        "220400", "220403", "238406", "43040A", "430400", "630403", "838406", "A3040A", "000000", "000000"
    ],
    "节奏步伐": [
        "210100", "210102", "210104", "210106", "210108", "21010A", "210100", "218102", "210105", "218107",
        "21010A", "210100", "210103", "218106", "21010A", "210100", "210105", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "000000"
    ],
    "心跳节奏": [
        "46130A", "46130A", "46130A", "46130A", "46130A", "46130A", "210100", "210100", "210100", "210100",
        "210100", "218107", "210108", "210109", "21010A", "210100", "210100", "210100", "210100", "210100",
        "210100", "210100", "210100", "210100", "210100", "218107", "210108", "210109", "21010A", "210100",
        "210100", "210100", "210100", "210100", "000000"
    ],
    "信号灯": [
        "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A",
        "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A", "25440A",
        "210100", "E10103", "C18206", "A1030A", "210100", "E10103", "C18206", "A1030A", "210100", "E10103",
        "C18206", "A1030A", "210100", "E10103", "C18206", "A1030A", "210100", "E10103", "C18206", "A1030A"
    ],
    "按捏渐强": [
        "210100", "218102", "210100", "210105", "210100", "210107", "210100", "218108", "210100", "21010A",
        "210100"
    ],
    "快速按捏": [
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "000000", "000000"
    ],
    "压缩": [
        "C4080A", "24080A", "84070A", "03070A", "63060A", "E3050A", "43050A", "A3040A", "22040A", "82030A",
        "02030A", "21010A", "21010A", "21010A", "21010A", "21010A", "21010A", "21010A", "21010A", "21010A",
        "21010A"
    ],
    "呼吸": [
        "210100", "210102", "210104", "210106", "210108", "21010A", "21010A", "21010A", "000000", "000000",
        "000000", "000000"
    ],
    "雨水冲刷": [
        "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103",
        "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106",
        "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A",
        "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "A10103", "A18106", "A1010A", "21070A",
        "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A",
        "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A",
        "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "21070A",
        "21070A", "21070A", "21070A", "21070A", "21070A", "21070A", "000000", "000000", "000000"
    ],
    "变速敲击": [
        "E1020A", "E1020A", "E1020A", "E10200", "E10200", "E10200", "E10200", "E1020A", "E1020A", "E1020A",
        "E10200", "E10200", "E10200", "E10200", "E1020A", "E1020A", "E1020A", "E10200", "E10200", "E10200",
        "E10200", "E1020A", "E1020A", "E1020A", "E10200", "E10200", "E10200", "E10200", "E1020A", "E1020A",
        "E1020A", "E10200", "E10200", "E10200", "E10200", "E1020A", "E1020A", "E1020A", "E10200", "E10200",
        "E10200", "E10200", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A",
        "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A",
        "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A",
        "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A", "A3130A",
        "000000", "000000"
    ],
    "波浪涟漪": [
        "210100", "210105", "21010A", "210107", "E20100", "E20105", "E2010A", "E20107", "E20200", "E20205",
        "E2020A", "E20207", "E20300", "E20305", "E2030A", "E20307", "A30400", "A30405", "A3040A", "A30407",
        "A30500", "A30505", "A3050A", "A30507", "A30600", "A30605", "A3060A", "A30607", "640700", "640705",
        "64070A", "640707", "640800", "640805", "64080A", "640807", "640900", "640905", "64090A", "640907",
        "440A00", "440A05", "440A0A", "440A07", "440B00", "440B05", "440B0A", "440B07", "250C00", "250C05",
        "250C0A", "250C07", "250D00", "250D05", "250D0A", "250D07", "000000"
    ],
    "颗粒摩擦": [
        "21010A", "41010A", "81010A", "C10100", "C1010A", "01020A", "41020A", "610200", "61020A", "A1020A",
        "E1020A", "210300", "21030A", "61030A", "81030A", "C10300", "C1030A", "01040A", "41040A", "810400",
        "81040A", "A1040A", "E1040A", "210500", "21050A", "61050A", "A1050A", "E10500"
    ],
    "挑逗2": [
        "810400", "210401", "E10302", "A10303", "610304", "018305", "C18206", "818207", "418208", "01020A",
        "810400", "210401", "E10302", "A10303", "610304", "018305", "C18206", "818207", "418208", "01020A",
        "810400", "210401", "E10302", "A10303", "610304", "018305", "C18206", "818207", "418208", "01020A",
        "810400", "210401", "E10302", "A10303", "610304", "018305", "C18206", "818207", "418208", "01020A",
        "210100", "41010A", "410100", "61010A", "610100", "81010A", "810100", "A1010A", "A10100", "C1010A",
        "C10100", "E1010A", "E10100", "01020A", "010200", "21020A", "210200", "41020A", "410200", "61020A",
        "610200", "81020A", "810200", "A1020A", "A10200", "C1020A", "C10200", "E1020A", "E10200", "01030A",
        "010300", "21030A", "210300", "41030A", "410300", "61030A", "610300", "81030A", "810300", "A1030A",
        "000000", "000000"
    ],
    "连击": [
        "21010A", "210100", "21010A", "218106", "210103", "210100", "210100", "210100"
    ],
    "挑逗1": [
        "210100", "618102", "A10105", "E18107", "21020A", "81020A", "C1020A", "010300", "410300", "A10300",
        "210100", "618102", "A10105", "E18107", "21020A", "81020A", "C1020A", "010300", "410300", "A10300",
        "210100", "618102", "A10105", "E18107", "21020A", "81020A", "C1020A", "010300", "410300", "A10300",
        "210100", "618102", "A10105", "E18107", "21020A", "81020A", "C1020A", "010300", "410300", "A10300",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A", "210100", "21010A",
        "210100", "21010A", "000000", "210100", "618102", "A10105", "E18107", "21020A", "81020A", "C1020A",
        "010300", "410300", "A10300"
    ],
    "潮汐": [
        "210100", "418101", "810103", "A10105", "E18106", "210208", "41020A", "810209", "A10208", "E18207",
        "218306", "210300", "418301", "810303", "A10305", "E18306", "210408", "41040A", "810409", "A10408",
        "E18407", "218506", "000000"
    ]
}

def parse_hex_wave_step(hex_string):
    """
    Parses a 6-character hex string (FF II HH) into (frequency, intensity) tuple, 
    assuming FF is frequency and HH is 0-10 scaled intensity, as per V2 protocol data format.
    """
    if len(hex_string) != 6:
        return (1, 0) # Default to minimum if invalid format
    
    try:
        # Freq: First 2 characters. Cap at 100 Hz (0x64).
        freq_hex = hex_string[0:2]
        raw_freq = int(freq_hex, 16)
        frequency = max(1, min(100, raw_freq))

        # Intensity: Last 2 characters, scaled 0-10 (0x00 - 0x0A).
        int_hex = hex_string[4:6]
        scaled_int = int(int_hex, 16)

        # Scale 0-10 to 0-100%
        if scaled_int > 10:
             # If value is unexpectedly high, cap at 100%
             intensity = 100
        else:
            intensity = math.floor((scaled_int / 10.0) * 100)
            
        return (frequency, intensity)

    except ValueError:
        return (1, 0) # Error during parsing

# 解析导入的波形
IMPORTED_WAVEFORMS = {}
for name, hex_list in USER_HEX_WAVEFORMS.items():
    IMPORTED_WAVEFORMS[name] = [parse_hex_wave_step(h) for h in hex_list]

# ==========================================
# 1. 波形定义 (频率Hz, 强度0-100)
# 每个列表代表 100ms 的波形步进。
# ==========================================
WAVEFORMS = {
    # 内置波形
    "纯脉冲 (瞬时触发)": [
        (10, 100), (10, 100), (10, 100), (10, 100) # 保持 400ms 的全输出
    ],
    "呼吸 (Breathe)": [
        (10, 0), (10, 20), (10, 40), (10, 60), (10, 80), (10, 100), 
        (10, 100), (10, 100), (10, 80), (10, 60), (10, 40), (10, 20), 
        (10, 0), (10, 0)
    ],
    "潮汐 (Tidal)": [
        (10, 0), (11, 16), (13, 33), (14, 50), (16, 66), (18, 83), 
        (19, 100), (18, 83), (16, 66), (14, 50), (13, 33), (11, 16), 
        (10, 0), (10, 0)
    ],
    
    # 新增波形
    "方波 (Square 50%)": [
        (20, 100), (20, 100), (20, 0), (20, 0)
    ],
    "升阶 (Ramp Up)": [
        (10, 0), (10, 25), (10, 50), (10, 75), (10, 100), (10, 0) 
    ],
    "心跳 (Heartbeat)": [
        (30, 90), (30, 30), (10, 0), (10, 0), (10, 0), (10, 0), (10, 0), (10, 0)
    ]
}

# 整合导入的波形
WAVEFORMS.update(IMPORTED_WAVEFORMS)


# ==========================================
# 1.1. 波形序列定义 (列表中的项目必须是 WAVEFORMS 的键)
# ==========================================
WAVEFORM_SEQUENCES = {
    "测试循环 (Test Loop)": ["呼吸 (Breathe)", "潮汐 (Tidal)", "心跳 (Heartbeat)", "方波 (Square 50%)"],
    "渐强循环 (Ramp Cycle)": ["升阶 (Ramp Up)", "潮汐 (Tidal)", "方波 (Square 50%)"],
}

COMBO_DURATION_STEPS = 4 

# ==========================================
# 2. DG-LAB V3 蓝牙控制核心 (底层协议)
# ==========================================
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
                if self.status_callback: self.status_callback("正在扫描郊狼设备...")
                device = await BleakScanner.find_device_by_filter(
                    lambda d, ad: d.name and ("47L121" in d.name or "D-LAB" in d.name or "Coyote" in d.name)
                )
                
                if not device:
                    if self.status_callback: self.status_callback("未找到设备，3秒后重试...")
                    await asyncio.sleep(3)
                    continue

                if self.status_callback: self.status_callback(f"尝试连接: {device.name} ...")
                async with BleakClient(device) as client:
                    self.client = client
                    
                    # 1. 发送 BF 指令设置软上限为 100 (0x64) 
                    bf_packet = bytearray([0xBF, 0x64, 0x64, 0x00, 0x00, 0x00, 0x00]) 
                    await client.write_gatt_char(self.UUID_WRITE, bf_packet)
                    if self.debug_callback: self.debug_callback("✅ 已发送 BF 指令 (设置软上限 100%)")
                    
                    if self.status_callback: self.status_callback("✅ 已连接! 脉冲循环启动")
                    
                    # 循环发送心跳包 (V3要求每100ms发送一次)
                    while client.is_connected and self.running:
                        packet = self._build_packet() 
                        await client.write_gatt_char(self.UUID_WRITE, packet)
                        if self.debug_callback and time.time() % 1.0 < 0.1:
                            self.debug_callback(f"[Heartbeat] Freq: {self.target_freq}Hz, Int A: {self.target_int_a}%, Int B: {self.target_int_b}%")
                            
                        await asyncio.sleep(0.1) # 100ms 间隔

            except Exception as e:
                error_msg = f"❌ 蓝牙错误: {e.__class__.__name__}"
                if "NotConnectedError" not in str(e):
                    error_msg += f" ({e})"
                if self.status_callback: self.status_callback(error_msg)
                await asyncio.sleep(3)
            finally:
                self.client = None

    def _build_packet(self):
        """构建 V3 B0指令: 使用存储的 target_freq, target_int_a, target_int_b"""
        
        freq = max(1, min(100, int(self.target_freq))) 
        val_a = max(0, min(100, int(self.target_int_a))) 
        val_b = max(0, min(100, int(self.target_int_b))) 
        
        parsing_method_and_seq = 0x0F 
        max_channel_strength = 0x64 # 100 
        
        packet = bytearray([0xB0, parsing_method_and_seq, max_channel_strength, max_channel_strength])
        
        # A 通道数据 (8 bytes): 频率*4 + 强度*4
        if self.channel_a_active:
            packet.extend([freq] * 4) 
            packet.extend([val_a] * 4)  
        else:
            packet.extend([0] * 8) 
        
        # B 通道数据 (8 bytes): 频率*4 + 强度*4
        if self.channel_b_active:
            packet.extend([freq] * 4) 
            packet.extend([val_b] * 4)  
        else:
            packet.extend([0] * 8) 
        
        return packet 

    def set_shock_split_wave(self, freq, intensity_a, intensity_b):
        """设置新的波形参数元组 (独立 A/B 强度)"""
        self.target_freq = freq
        self.target_int_a = intensity_a
        self.target_int_b = intensity_b
        
    def set_channels(self, a_active, b_active):
        self.channel_a_active = a_active
        self.channel_b_active = b_active

# ==========================================
# 3. UI 与 业务逻辑
# ==========================================
class GameControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KemoPop 实时电击控制器")
        self.root.geometry("1000x800")
        
        self.bt_ctrl = DGLabV3Controller()
        self.bt_ctrl.status_callback = self.update_bt_status
        self.bt_ctrl.debug_callback = self.log_dglab_debug 
        self.bt_ctrl.start_thread()

        self.game_process = None
        self.shock_enabled = False 
        self.log_queue = queue.Queue()
        self.debug_queue = queue.Queue()
        
        # --- UI Setup ---
        self.var_log_visible = tk.BooleanVar(value=True) # Log visibility toggle
        
        # --- 常规波形 A/B 独立强度控制变量：默认 Min=0, Max=2 ---
        self.var_routine_min_a = tk.IntVar(value=0) 
        self.var_routine_max_a = tk.IntVar(value=2) 
        self.var_routine_min_b = tk.IntVar(value=0) 
        self.var_routine_max_b = tk.IntVar(value=2) 
        
        # --- Combo 增强 A/B 独立强度控制变量：默认 Min=10, Max=30 ---
        self.var_combo_min_a = tk.IntVar(value=10) 
        self.var_combo_max_a = tk.IntVar(value=30) 
        self.var_combo_min_b = tk.IntVar(value=10) 
        self.var_combo_max_b = tk.IntVar(value=30) 
        
        self.var_score_limit = tk.IntVar(value=500)
        
        # --- 波形/序列 播放状态 ---
        self.routine_pattern_name = "呼吸 (Breathe)" 
        self.is_sequence_mode = False                 
        self.sequence_pattern_index = 0               
        # 初始化时使用合并后的 WAVEFORMS
        self.routine_steps = WAVEFORMS[self.routine_pattern_name] 
        self.routine_step_index = 0                   
        self.pattern_timer = None
        
        # --- 波形播放速度控制 ---
        self.var_playback_interval = tk.IntVar(value=100) # 步进间隔 (ms)
        
        # --- 波形重复次数控制 ---
        self.var_repeat_count = tk.IntVar(value=1)      
        self.current_pattern_repeat_count = 0           
        
        # 瞬时增强波形状态
        self.combo_pattern_name = "纯脉冲 (瞬时触发)"
        self.combo_steps = WAVEFORMS[self.combo_pattern_name]
        self.combo_step_index = 0
        self.shock_override_timer = None
        self.is_overriding = False

        self._setup_ui()
        self._update_channels() 
        self.root.after(20, self.consume_logs)
        self.root.after(50, self.consume_debugs)
        
    # NEW: Log visibility toggle function
    def _toggle_log_visibility(self):
        """Toggles the visibility of the log container frame."""
        if self.var_log_visible.get():
            # Currently visible, hide it
            self.log_container_frame.pack_forget()
            self.btn_log_toggle.config(text="显示 Log 窗口 (Show)")
            self.var_log_visible.set(False)
            self.log_msg("⚠️ 已关闭 Log 窗口显示，以优化性能。游戏逻辑解析仍在后台运行。", is_game_log=False)
        else:
            # Currently hidden, show it
            self.log_container_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            self.btn_log_toggle.config(text="隐藏 Log 窗口 (Hide)")
            self.var_log_visible.set(True)
            self.log_msg("✅ 已开启 Log 窗口显示。", is_game_log=False)
            
    # --- 辅助函数：间隔输入验证 ---
    def _validate_interval(self):
        try:
            value = int(self.var_interval_str.get()) 
            if value < 50: 
                value = 50
            elif value > 1000: 
                value = 1000
            
            self.var_playback_interval.set(value)
            self.var_interval_str.set(str(value))
            self.log_msg(f"✅ 波形步进间隔设定为: {value} ms。", is_game_log=False)
            
            if self.shock_enabled and not self.is_overriding:
                 self._start_pattern_player() 
            
        except ValueError:
            self.var_interval_str.set(str(self.var_playback_interval.get()))
            self.log_msg("⚠️ 间隔输入无效，请输入50-1000范围内的整数。", is_game_log=False)
            
    # --- 辅助函数：重复次数输入验证 ---
    def _validate_repeat_count(self):
        try:
            value = int(self.var_repeat_count_str.get()) 
            if value < 1:
                value = 1
            elif value > 99: 
                value = 99
            
            self.var_repeat_count.set(value)
            self.var_repeat_count_str.set(str(value))
            self.current_pattern_repeat_count = 0 
            self.log_msg(f"✅ 重复次数设定为: {value} 次。", is_game_log=False)
            
        except ValueError:
            self.var_repeat_count_str.set(str(self.var_repeat_count.get()))
            self.log_msg("⚠️ 重复次数输入无效，请输入1-99范围内的整数。", is_game_log=False)
            
    # --- UI Setup Helper ---
    def _validate_and_update_int(self, string_var, int_var):
        """Safely parses string input, validates range (0-100), and updates IntVar."""
        try:
            value = int(string_var.get())
            if value < 0:
                value = 0
            elif value > 100:
                value = 100
            
            int_var.set(value)
            string_var.set(str(value))
        except ValueError:
            string_var.set(str(int_var.get()))
            self.log_msg("⚠️ 输入无效，请输入0-100范围内的整数。", is_game_log=False)

    def _add_intensity_controls(self, parent_frame, channel_name, var_min, var_max):
        """添加 Min/Max 强度滑动条和文字输入框"""
        
        # --- Min Control ---
        min_frame = ttk.Frame(parent_frame)
        min_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(min_frame, text=f"最低强度 (Min):").pack(side=tk.LEFT, anchor="w")
        
        min_entry_var = tk.StringVar(value=str(var_min.get()))
        min_entry = ttk.Entry(min_frame, textvariable=min_entry_var, width=5)
        min_entry.pack(side=tk.RIGHT, padx=(10, 0))
        min_entry.bind("<Return>", lambda event: self._validate_and_update_int(min_entry_var, var_min))
        min_entry.bind("<FocusOut>", lambda event: self._validate_and_update_int(min_entry_var, var_min))

        ttk.Scale(parent_frame, from_=0, to=50, variable=var_min, orient="horizontal").pack(fill="x", padx=5, pady=0)
        var_min.trace_add("write", lambda *args: min_entry_var.set(var_min.get())) 

        # --- Max Control ---
        max_frame = ttk.Frame(parent_frame)
        max_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(max_frame, text=f"最大强度 (Max):").pack(side=tk.LEFT, anchor="w")

        max_entry_var = tk.StringVar(value=str(var_max.get()))
        max_entry = ttk.Entry(max_frame, textvariable=max_entry_var, width=5)
        max_entry.pack(side=tk.RIGHT, padx=(10, 0))
        max_entry.bind("<Return>", lambda event: self._validate_and_update_int(max_entry_var, var_max))
        max_entry.bind("<FocusOut>", lambda event: self._validate_and_update_int(max_entry_var, var_max))

        ttk.Scale(parent_frame, from_=0, to=100, variable=var_max, orient="horizontal").pack(fill="x", padx=5, pady=0)
        var_max.trace_add("write", lambda *args: max_entry_var.set(var_max.get())) 

    # --- UI Setup ---
    def _setup_ui(self):
        paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 左侧：Log/Toggle 区域 ---
        left_frame = ttk.Frame(paned_main) 
        paned_main.add(left_frame, weight=66) 
        
        # Log Toggle Frame
        log_toggle_frame = ttk.Frame(left_frame)
        log_toggle_frame.pack(fill="x", padx=2, pady=2)
        
        self.btn_log_toggle = ttk.Button(
            log_toggle_frame, 
            text="隐藏 Log 窗口 (Hide)", 
            command=self._toggle_log_visibility
        )
        self.btn_log_toggle.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Log Container Frame to hold the two logs
        self.log_container_frame = ttk.Frame(left_frame)
        self.log_container_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2) 

        # --- Game Log Frame (now packed into log_container_frame) ---
        log_game_frame = ttk.LabelFrame(self.log_container_frame, text="▲ 游戏实时监控 Log (Kemopop! Log)")
        log_game_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.log_game_text = scrolledtext.ScrolledText(log_game_frame, state='disabled', bg='#1e1e1e', fg='#00ff00', font=("Consolas", 10), height=15)
        self.log_game_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- DG-LAB Log Frame (now packed into log_container_frame) ---
        log_dglab_frame = ttk.LabelFrame(self.log_container_frame, text="▼ DG-LAB 调试输出 Log (Bluetooth Debug)")
        log_dglab_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.log_dglab_text = scrolledtext.ScrolledText(log_dglab_frame, state='disabled', bg='#2c2c2c', fg='#ffaaaa', font=("Consolas", 10), height=5)
        self.log_dglab_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)


        # --- 右侧：控制页面 ---
        right_frame = ttk.Frame(paned_main)
        paned_main.add(right_frame, weight=34)

        # 1. 状态显示区
        status_frame = ttk.LabelFrame(right_frame, text="系统状态")
        status_frame.pack(fill="x", padx=10, pady=10)
        self.lbl_bt = ttk.Label(status_frame, text="蓝牙: 初始化...", foreground="blue")
        self.lbl_bt.pack(pady=5, anchor="w")
        self.lbl_game = ttk.Label(status_frame, text="游戏: 未运行", foreground="gray")
        self.lbl_game.pack(pady=5, anchor="w")
        
        # 2. 常规波形/序列选择 (合并了波形和序列)
        wave_routine_frame = ttk.LabelFrame(right_frame, text="常规波形/序列播放控制")
        wave_routine_frame.pack(fill="x", padx=10, pady=5)
        
        # 2a. 波形/序列选择下拉框
        ttk.Label(wave_routine_frame, text="选择波形/序列:").pack(anchor="w", padx=5, pady=2)
        # 更新下拉列表，包含所有合并后的波形键
        all_routine_options = list(WAVEFORMS.keys()) + list(WAVEFORM_SEQUENCES.keys())
        self.var_routine_wave = tk.StringVar(value=self.routine_pattern_name)
        self.wave_routine_combo = ttk.Combobox(wave_routine_frame, textvariable=self.var_routine_wave, values=all_routine_options, state="readonly")
        self.wave_routine_combo.pack(fill="x", padx=5, pady=5)
        self.wave_routine_combo.bind("<<ComboboxSelected>>", self._change_routine_selection)
        
        # 2b. 波形重复次数输入框
        repeat_frame = ttk.Frame(wave_routine_frame)
        repeat_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(repeat_frame, text="序列中波形重复次数 (Repeat):").pack(side=tk.LEFT, anchor="w")
        
        self.var_repeat_count_str = tk.StringVar(value=str(self.var_repeat_count.get()))
        repeat_entry = ttk.Entry(repeat_frame, textvariable=self.var_repeat_count_str, width=5)
        repeat_entry.pack(side=tk.RIGHT)
        repeat_entry.bind("<Return>", lambda event: self._validate_repeat_count())
        repeat_entry.bind("<FocusOut>", lambda event: self._validate_repeat_count())
        
        # 2c. 波形步进间隔输入框
        speed_frame = ttk.Frame(wave_routine_frame)
        speed_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(speed_frame, text="波形步进间隔 (ms):").pack(side=tk.LEFT, anchor="w")
        
        self.var_interval_str = tk.StringVar(value=str(self.var_playback_interval.get()))
        interval_entry = ttk.Entry(speed_frame, textvariable=self.var_interval_str, width=5)
        interval_entry.pack(side=tk.RIGHT)
        interval_entry.bind("<Return>", lambda event: self._validate_interval())
        interval_entry.bind("<FocusOut>", lambda event: self._validate_interval())

        ttk.Scale(wave_routine_frame, from_=50, to=1000, variable=self.var_playback_interval, orient="horizontal").pack(fill="x", padx=5, pady=0)
        self.var_playback_interval.trace_add("write", lambda *args: self.var_interval_str.set(self.var_playback_interval.get()))
        
        # 3. Combo 增强波形选择
        wave_combo_frame = ttk.LabelFrame(right_frame, text="Combo 增强波形 (瞬时触发)")
        wave_combo_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(wave_combo_frame, text="增强波形:").pack(anchor="w", padx=5, pady=2)
        self.var_combo_wave = tk.StringVar(value=self.combo_pattern_name)
        # 更新 Combo 波形下拉列表
        self.wave_combo_combo = ttk.Combobox(wave_combo_frame, textvariable=self.var_combo_wave, values=list(WAVEFORMS.keys()), state="readonly")
        self.wave_combo_combo.pack(fill="x", padx=5, pady=5)
        self.wave_combo_combo.bind("<<ComboboxSelected>>", self._change_combo_waveform)

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        # 4. A 通道常规强度控制 (Routine)
        ctrl_a_routine_frame = ttk.LabelFrame(right_frame, text="A 通道 常规强度配置 (Routine Min/Max)")
        ctrl_a_routine_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_a_routine_frame, "A", self.var_routine_min_a, self.var_routine_max_a)

        # 5. B 通道常规强度控制 (Routine)
        ctrl_b_routine_frame = ttk.LabelFrame(right_frame, text="B 通道 常规强度配置 (Routine Min/Max)")
        ctrl_b_routine_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_b_routine_frame, "B", self.var_routine_min_b, self.var_routine_max_b)
        
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)
        
        # 6. A 通道 Combo 强度控制 (NEW)
        ctrl_a_combo_frame = ttk.LabelFrame(right_frame, text="A 通道 Combo 增强强度配置 (Combo Min/Max)")
        ctrl_a_combo_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_a_combo_frame, "A-Combo", self.var_combo_min_a, self.var_combo_max_a)

        # 7. B 通道 Combo 强度控制 (NEW)
        ctrl_b_combo_frame = ttk.LabelFrame(right_frame, text="B 通道 Combo 增强强度配置 (Combo Min/Max)")
        ctrl_b_combo_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_b_combo_frame, "B-Combo", self.var_combo_min_b, self.var_combo_max_b)

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        # 8. 灵敏度 (Score limit)
        score_frame = ttk.LabelFrame(right_frame, text="游戏参数")
        score_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(score_frame, text="满力分数阈值 (Total Score):").pack(anchor="w", padx=5)
        ttk.Scale(score_frame, from_=100, to=2000, variable=self.var_score_limit, orient="horizontal").pack(fill="x", padx=5, pady=5)
        ttk.Label(score_frame, textvariable=self.var_score_limit).pack()
        
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)
        
        # 9. 通道选择
        channel_frame = ttk.LabelFrame(right_frame, text="输出通道选择")
        channel_frame.pack(fill="x", padx=10, pady=5)
        self.var_ch_a = tk.BooleanVar(value=True)
        self.var_ch_b = tk.BooleanVar(value=True)
        self.var_ch_a.trace_add("write", lambda *args: self._update_channels())
        self.var_ch_b.trace_add("write", lambda *args: self._update_channels())
        ttk.Checkbutton(channel_frame, text="A 通道 (左)", variable=self.var_ch_a).pack(anchor="w", padx=5)
        ttk.Checkbutton(channel_frame, text="B 通道 (右)", variable=self.var_ch_b).pack(anchor="w", padx=5)

        # 10. 实时输出显示
        self.lbl_output = ttk.Label(right_frame, text="OUTPUT: 0%", font=("Arial", 24, "bold"), foreground="#cc0000")
        self.lbl_output.pack(pady=30)

        # 11. 启动按钮
        self.btn_run = ttk.Button(right_frame, text="启动游戏 (kemopop.exe)", command=self.run_game)
        self.btn_run.pack(pady=10, fill='x', padx=20)
    
    # --- 波形播放器逻辑 ---

    def _load_current_routine(self):
        """根据当前模式和索引加载下一个波形的步进数据"""
        
        current_pattern_name = self.routine_pattern_name
        
        if self.is_sequence_mode:
            sequence_list = WAVEFORM_SEQUENCES.get(self.routine_pattern_name)
            if not sequence_list:
                self.log_msg(f"❌ 序列 '{self.routine_pattern_name}' 不存在！恢复到呼吸波形。", is_game_log=True)
                self.is_sequence_mode = False
                self.routine_pattern_name = "呼吸 (Breathe)"
                current_pattern_name = "呼吸 (Breathe)"
                
            else:
                # 确保索引在有效范围内，并循环
                self.sequence_pattern_index %= len(sequence_list)
                current_pattern_name = sequence_list[self.sequence_pattern_index]

            self.routine_steps = WAVEFORMS.get(current_pattern_name, WAVEFORMS["呼吸 (Breathe)"])
            self.log_msg(f"📝 序列播放: 切换到波形 '{current_pattern_name}'", is_game_log=False)
        else:
            # 单一波形模式
            self.routine_steps = WAVEFORMS.get(self.routine_pattern_name, WAVEFORMS["呼吸 (Breathe)"])

        self.routine_step_index = 0
        
    def _change_routine_selection(self, event=None):
        new_name = self.var_routine_wave.get()
        self.routine_pattern_name = new_name
        
        if new_name in WAVEFORM_SEQUENCES:
            self.is_sequence_mode = True
            self.sequence_pattern_index = 0
            self.log_msg(f"📝 常规模式切换为序列: {new_name}", is_game_log=True)
        else:
            self.is_sequence_mode = False
            self.log_msg(f"📝 常规模式切换为单一波形: {new_name}", is_game_log=True)
        
        self.current_pattern_repeat_count = 0 
        self._load_current_routine()
        
        if self.shock_enabled and not self.is_overriding:
            self._start_pattern_player()

    def _change_combo_waveform(self, event=None):
        new_name = self.var_combo_wave.get()
        self.combo_pattern_name = new_name
        self.combo_steps = WAVEFORMS.get(new_name, WAVEFORMS["纯脉冲 (瞬时触发)"])
        self.log_msg(f"📝 Combo 波形切换为: {new_name}")

    def _start_pattern_player(self):
        if self.pattern_timer:
            self.root.after_cancel(self.pattern_timer)
            
        self.current_pattern_repeat_count = 0 
        self._load_current_routine()
        self.log_msg(f"▶️ 启动常规播放器: {self.routine_pattern_name}", is_game_log=True)
        self._next_pattern_step()

    def _stop_pattern_player(self):
        if self.pattern_timer:
            self.root.after_cancel(self.pattern_timer)
            self.pattern_timer = None
        self.log_msg("⏸️ 停止波形播放器", is_game_log=True)
        
    def _next_pattern_step(self):
        """推进波形步进，独立计算 A/B 强度 (使用 Routine 变量)"""
        if self.is_overriding:
            # 如果正在播放 Combo (覆盖模式)，则跳过常规波形步进
            interval_ms = self.var_playback_interval.get() 
            self.pattern_timer = self.root.after(interval_ms, self._next_pattern_step)
            return

        # 1. 取得当前步进的原始波形值
        step_data = self.routine_steps[self.routine_step_index]
        wave_freq_raw, wave_int_raw = step_data
        
        # 2. --- Channel A Calculation (使用 Routine 变量) ---
        min_a, max_a = self.var_routine_min_a.get(), self.var_routine_max_a.get() 
        scaled_intensity_a = (wave_int_raw / 100) * (max_a - min_a)
        final_intensity_a = int(min_a + scaled_intensity_a)
        final_intensity_a = min(100, max(0, final_intensity_a))

        # 3. --- Channel B Calculation (使用 Routine 变量) ---
        min_b, max_b = self.var_routine_min_b.get(), self.var_routine_max_b.get() 
        scaled_intensity_b = (wave_int_raw / 100) * (max_b - min_b)
        final_intensity_b = int(min_b + scaled_intensity_b)
        final_intensity_b = min(100, max(0, final_intensity_b))

        # 4. 发送指令
        self.bt_ctrl.set_shock_split_wave(wave_freq_raw, final_intensity_a, final_intensity_b)
        
        # 实时显示当前播放的波形名称
        current_pattern_name = self.var_routine_wave.get()
        if self.is_sequence_mode:
            current_pattern_name = WAVEFORM_SEQUENCES[self.routine_pattern_name][self.sequence_pattern_index]
        
        self.lbl_output.config(text=f"WAVE: A={final_intensity_a}%, B={final_intensity_b}% @ {wave_freq_raw}Hz ({current_pattern_name})", foreground="#cc0000")

        # 5. 步进到下一状态
        self.routine_step_index += 1
        
        if self.routine_step_index >= len(self.routine_steps):
            # 当前波形播放结束一个周期
            
            self.current_pattern_repeat_count += 1
            repeat_limit = self.var_repeat_count.get()
            
            if self.is_sequence_mode and self.current_pattern_repeat_count >= repeat_limit:
                # 播放完成设定的重复次数，切换到序列中的下一个波形
                self.sequence_pattern_index += 1
                self.current_pattern_repeat_count = 0 # 重置重复计数
                self._load_current_routine() 
            else:
                # 序列模式但重复次数未到，或者单一波形模式（只需重置步进索引）
                self.routine_step_index = 0
                
                if self.is_sequence_mode:
                    self.log_msg(f"📝 {current_pattern_name} 重复: {self.current_pattern_repeat_count}/{repeat_limit}", is_game_log=False)
        
        # 6. 调度下一次步进 (使用用户设定的间隔)
        interval_ms = self.var_playback_interval.get()
        self.pattern_timer = self.root.after(interval_ms, self._next_pattern_step)
        
    # --- 游戏事件与蓝牙状态 ---
    
    def _trigger_shock(self, score):
        """根据分数计算增强强度，短暂覆盖当前波形，播放 Combo 波形"""
        if not self.shock_enabled:
            return

        self.is_overriding = True
        self.combo_step_index = 0
        
        if self.shock_override_timer:
            self.root.after_cancel(self.shock_override_timer)
            
        self.log_msg(f"⚡ Combo 触发! 开始播放 {self.combo_pattern_name}", is_game_log=True)
        
        self._play_combo_step(score)


    def _play_combo_step(self, trigger_score):
        """播放 Combo 波形的一个步进，独立计算 A/B 强度 (使用 Combo 变量)"""
        if not self.is_overriding or self.combo_step_index >= COMBO_DURATION_STEPS:
            self.is_overriding = False
            self.shock_override_timer = None
            self.log_msg("⚡ Combo 结束，恢复常规波形播放", is_game_log=True)
            # 恢复常规播放器
            self.root.after(0, self._next_pattern_step) 
            return

        # 1. 计算 Combo 脉冲的增强乘数
        limit = self.var_score_limit.get()
        score_multiplier = min(trigger_score / limit, 1.0)
        
        # 2. 获取 Combo 波形的原始数据
        step_data = self.combo_steps[self.combo_step_index % len(self.combo_steps)]
        wave_freq_raw, wave_int_raw = step_data
        
        # 3. --- Channel A Calculation (使用 Combo 变量) ---
        min_a, max_a = self.var_combo_min_a.get(), self.var_combo_max_a.get() 
        scaled_base_a = (wave_int_raw / 100) * (max_a - min_a)
        final_intensity_a = int(min_a + (scaled_base_a * score_multiplier))
        final_intensity_a = min(100, max(0, final_intensity_a))
        
        # 4. --- Channel B Calculation (使用 Combo 变量) ---
        min_b, max_b = self.var_combo_min_b.get(), self.var_combo_max_b.get() 
        scaled_base_b = (wave_int_raw / 100) * (max_b - min_b)
        final_intensity_b = int(min_b + (scaled_base_b * score_multiplier))
        final_intensity_b = min(100, max(0, final_intensity_b))
        
        # 5. 发送指令
        self.bt_ctrl.set_shock_split_wave(wave_freq_raw, final_intensity_a, final_intensity_b)
        self.lbl_output.config(text=f"COMBO: A={final_intensity_a}%, B={final_intensity_b}% (Multi: {score_multiplier:.2f})", foreground="#00aaff")

        # 6. 步进并调度下一帧 (Combo 固定 100ms 间隔)
        self.combo_step_index += 1
        self.shock_override_timer = self.root.after(100, lambda: self._play_combo_step(trigger_score))

    # --- 辅助函数 ---
    
    # *** 优化点：_write_log 在 Log 窗口隐藏时，跳过昂贵的 UI 写入操作 ***
    def _write_log(self, widget, line, is_game_log): 
        """Safely writes to a ScrolledText widget, skipping UI update if not visible."""
        
        # 如果 Log 窗口被隐藏，直接返回，跳过 UI 写入和调度
        if not self.var_log_visible.get():
            return

        def update():
            widget.configure(state='normal')
            widget.insert(tk.END, line + "\n")
            widget.see(tk.END)
            widget.configure(state='disabled')
        self.root.after(0, update)
        
    def log_dglab_debug(self, msg):
        self.debug_queue.put(msg)
        
    def consume_debugs(self):
        """Processes Bluetooth debug logs, calls _write_log with is_game_log=False."""
        while not self.debug_queue.empty():
            line = self.debug_queue.get_nowait()
            self._write_log(self.log_dglab_text, line, is_game_log=False)
        self.root.after(50, self.consume_debugs)
        
    def consume_logs(self):
        """Processes game logs, writes to UI only if visible, and always runs _parse_logic."""
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            
            # 关键优化：_write_log 会根据 self.var_log_visible 决定是否执行 UI 写入
            self._write_log(self.log_game_text, line, is_game_log=True)
            
            # 解析逻辑必须始终运行，以确保游戏联动功能正常
            self._parse_logic(line)
            
        self.root.after(20, self.consume_logs)
        
    def log_msg(self, msg, is_game_log=False):
        """Writes custom messages to the log, skipping UI update if not visible."""
        # 如果 Log 窗口被隐藏，跳过消息写入，除非是状态更新
        if not self.var_log_visible.get() and not is_game_log:
            return
            
        log_widget = self.log_game_text if is_game_log else self.log_dglab_text
        
        def update():
            # 再次检查，防止在 after 调度期间状态被改变
            if not self.var_log_visible.get() and not is_game_log:
                return
                
            log_widget.configure(state='normal')
            log_widget.insert(tk.END, f"--- {msg} ---\n")
            log_widget.see(tk.END)
            log_widget.configure(state='disabled')
        self.root.after(0, update)
        
    def _update_channels(self):
        a_active = self.var_ch_a.get()
        b_active = self.var_ch_b.get()
        if not a_active and not b_active:
            self.log_msg("⚠️ 警告: 未选择通道，电流输出已停止！")
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self.bt_ctrl.set_channels(False, False)
        else:
            self.bt_ctrl.set_channels(a_active, b_active)
            self.log_msg(f"✅ 通道设置更新: A={a_active}, B={b_active}")
            if self.shock_enabled and not self.is_overriding: self._start_pattern_player() 
    
    def update_bt_status(self, msg):
        self.root.after(0, lambda: self.lbl_bt.config(text=msg))
        
    def run_game(self):
        game_path = "kemopop.exe"
        full_path = os.path.join(os.getcwd(), game_path)
        if not os.path.exists(full_path):
            self.log_msg(f"❌ 错误: 找不到文件 {full_path}")
            return
        self.btn_run.config(state="disabled", text="游戏运行中...")
        self.lbl_game.config(text="游戏: 运行中 (等待信号)", foreground="orange")
        self.log_msg(f"🚀 正在启动: {game_path}", is_game_log=True)
        t = threading.Thread(target=self._process_thread, args=([game_path],), daemon=True)
        t.start()
        
    def _process_thread(self, cmd_list):
        try:
            process = subprocess.Popen(
                cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, text=True, bufsize=1, errors='replace'
            )
            self.game_process = process
            
            # 注意: 必须持续读取 stdout，否则子进程的缓冲区可能会满，导致子进程（游戏）卡死。
            # 性能优化在 log_queue 消费端（consume_logs）进行。
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None: break
                if line: self.log_queue.put(line.strip())
                
            self.log_queue.put(">>> GAME CLOSED <<<")
            
        except Exception as e:
            self.log_queue.put(f"启动异常: {e}")
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal", text="启动游戏 (kemopop.exe)"))
            self.root.after(0, lambda: self.lbl_game.config(text="游戏: 已停止", foreground="red"))
            self.shock_enabled = False
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self._stop_pattern_player()
            
    def _parse_logic(self, line):
        if "[Beats] Crossfade 0 -> 0" in line:
            self.shock_enabled = True
            self.lbl_game.config(text="状态: 游戏中 (⚡电击已启用)", foreground="green")
            self.log_msg(">>> 检测到游戏开始，波形播放器启动 <<<", is_game_log=True)
            self._start_pattern_player() 
        elif "Writing player records" in line:
            self.shock_enabled = False
            self.lbl_game.config(text="状态: 结算中 (电击停止)", foreground="blue")
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self._stop_pattern_player() 
            self.lbl_output.config(text="OUTPUT: 0% (停止)")
            self.log_msg(">>> 检测到结算，停止输出 <<<", is_game_log=True)
        elif "[Chain] TOTAL SCORE:" in line:
            match = re.search(r"TOTAL SCORE:\s+(\d+)", line)
            if match and self.shock_enabled:
                score = int(match.group(1))
                self._trigger_shock(score)

if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
             pass 
             
    root = tk.Tk()
    app = GameControllerApp(root)
    root.mainloop()
