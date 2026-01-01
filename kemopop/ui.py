import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import threading
import queue
import re
import time
import sys
import os

from .controller import DGLabV3Controller
from .waveforms import WAVEFORMS, WAVEFORM_SEQUENCES, COMBO_DURATION_STEPS
from . import i18n
from .config import load_config, save_config


class GameControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(i18n.t("app_title"))
        self.root.geometry("1000x800")
        
        # Load saved configuration
        self.config = load_config()
        self.game_path = self.config.get("game_path", "kemopop.exe")

        self.bt_ctrl = DGLabV3Controller()
        self.bt_ctrl.status_callback = self.update_bt_status
        self.bt_ctrl.debug_callback = self.log_dglab_debug
        self.bt_ctrl.start_thread()

        self.game_process = None
        self.shock_enabled = False
        self.log_queue = queue.Queue()
        self.debug_queue = queue.Queue()

        self.var_log_visible = tk.BooleanVar(value=True)

        self.var_routine_min_a = tk.IntVar(value=self.config.get("routine_min_a", 0))
        self.var_routine_max_a = tk.IntVar(value=self.config.get("routine_max_a", 2))
        self.var_routine_min_b = tk.IntVar(value=self.config.get("routine_min_b", 0))
        self.var_routine_max_b = tk.IntVar(value=self.config.get("routine_max_b", 2))

        self.var_combo_min_a = tk.IntVar(value=self.config.get("combo_min_a", 10))
        self.var_combo_max_a = tk.IntVar(value=self.config.get("combo_max_a", 30))
        self.var_combo_min_b = tk.IntVar(value=self.config.get("combo_min_b", 10))
        self.var_combo_max_b = tk.IntVar(value=self.config.get("combo_max_b", 30))

        self.var_score_limit = tk.IntVar(value=self.config.get("score_limit", 500))

        self.routine_pattern_name = "呼吸 (Breathe)"
        self.is_sequence_mode = False
        self.sequence_pattern_index = 0
        self.routine_steps = WAVEFORMS[self.routine_pattern_name]
        self.routine_step_index = 0
        self.pattern_timer = None

        self.var_playback_interval = tk.IntVar(value=self.config.get("playback_interval", 100))
        self.var_repeat_count = tk.IntVar(value=self.config.get("repeat_count", 1))
        self.current_pattern_repeat_count = 0

        self.combo_pattern_name = "纯脉冲 (瞬时触发)"
        self.combo_steps = WAVEFORMS[self.combo_pattern_name]
        self.combo_step_index = 0
        self.shock_override_timer = None
        self.is_overriding = False

        self._setup_ui()
        self._update_channels()
        self.root.after(20, self.consume_logs)
        self.root.after(50, self.consume_debugs)
        
        # Save config on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _toggle_log_visibility(self):
        if self.var_log_visible.get():
            self.log_container_frame.pack_forget()
            self.btn_log_toggle.config(text=i18n.t("show_log"))
            self.var_log_visible.set(False)
            self.log_msg(i18n.t("log_closed_msg"), is_game_log=False)
        else:
            self.log_container_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            self.btn_log_toggle.config(text=i18n.t("hide_log"))
            self.var_log_visible.set(True)
            self.log_msg(i18n.t("log_opened_msg"), is_game_log=False)

    def _validate_interval(self):
        try:
            value = int(self.var_interval_str.get())
            if value < 50:
                value = 50
            elif value > 1000:
                value = 1000

            self.var_playback_interval.set(value)
            self.var_interval_str.set(str(value))
            self.log_msg(i18n.t("interval_set_msg", value=value), is_game_log=False)

            if self.shock_enabled and not self.is_overriding:
                self._start_pattern_player()

        except ValueError:
            self.var_interval_str.set(str(self.var_playback_interval.get()))
            self.log_msg(i18n.t("interval_invalid_msg"), is_game_log=False)

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
            self.log_msg(i18n.t("repeat_set_msg", value=value), is_game_log=False)

        except ValueError:
            self.var_repeat_count_str.set(str(self.var_repeat_count.get()))
            self.log_msg(i18n.t("repeat_invalid_msg"), is_game_log=False)

    def _validate_and_update_int(self, string_var, int_var):
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
            self.log_msg(i18n.t("input_invalid_0_100"), is_game_log=False)

    def _add_intensity_controls(self, parent_frame, channel_name, var_min, var_max):
        min_frame = ttk.Frame(parent_frame)
        min_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(min_frame, text=i18n.t("label_min")).pack(side=tk.LEFT, anchor="w")

        min_entry_var = tk.StringVar(value=str(var_min.get()))
        min_entry = ttk.Entry(min_frame, textvariable=min_entry_var, width=5)
        min_entry.pack(side=tk.RIGHT, padx=(10, 0))
        min_entry.bind("<Return>", lambda event: self._validate_and_update_int(min_entry_var, var_min))
        min_entry.bind("<FocusOut>", lambda event: self._validate_and_update_int(min_entry_var, var_min))

        ttk.Scale(parent_frame, from_=0, to=50, variable=var_min, orient="horizontal").pack(fill="x", padx=5, pady=0)
        var_min.trace_add("write", lambda *args: min_entry_var.set(var_min.get()))

        max_frame = ttk.Frame(parent_frame)
        max_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(max_frame, text=i18n.t("label_max")).pack(side=tk.LEFT, anchor="w")

        max_entry_var = tk.StringVar(value=str(var_max.get()))
        max_entry = ttk.Entry(max_frame, textvariable=max_entry_var, width=5)
        max_entry.pack(side=tk.RIGHT, padx=(10, 0))
        max_entry.bind("<Return>", lambda event: self._validate_and_update_int(max_entry_var, var_max))
        max_entry.bind("<FocusOut>", lambda event: self._validate_and_update_int(max_entry_var, var_max))

        ttk.Scale(parent_frame, from_=0, to=100, variable=var_max, orient="horizontal").pack(fill="x", padx=5, pady=0)
        var_max.trace_add("write", lambda *args: max_entry_var.set(var_max.get()))

    def _setup_ui(self):
        paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(paned_main)
        paned_main.add(left_frame, weight=66)

        log_toggle_frame = ttk.Frame(left_frame)
        log_toggle_frame.pack(fill="x", padx=2, pady=2)

        self.btn_log_toggle = ttk.Button(
            log_toggle_frame,
            text=i18n.t("hide_log"),
            command=self._toggle_log_visibility
        )
        self.btn_log_toggle.pack(side=tk.LEFT, padx=5, pady=5)

        self.log_container_frame = ttk.Frame(left_frame)
        self.log_container_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        log_game_frame = ttk.LabelFrame(self.log_container_frame, text=i18n.t("log_game_frame_title"))
        log_game_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.log_game_text = scrolledtext.ScrolledText(log_game_frame, state='disabled', bg='#1e1e1e', fg='#00ff00', font=("Consolas", 10), height=15)
        self.log_game_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        log_dglab_frame = ttk.LabelFrame(self.log_container_frame, text=i18n.t("log_dglab_frame_title"))
        log_dglab_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.log_dglab_text = scrolledtext.ScrolledText(log_dglab_frame, state='disabled', bg='#2c2c2c', fg='#ffaaaa', font=("Consolas", 10), height=5)
        self.log_dglab_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        right_frame = ttk.Frame(paned_main)
        paned_main.add(right_frame, weight=34)

        # Create scrollable right panel
        right_canvas = tk.Canvas(right_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=right_canvas.yview)
        scrollable_right_frame = ttk.Frame(right_canvas)
        
        scrollable_right_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        
        right_canvas.create_window((0, 0), window=scrollable_right_frame, anchor="nw")
        right_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        right_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        status_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("status_frame_title"))
        status_frame.pack(fill="x", padx=10, pady=10)
        self.lbl_bt = ttk.Label(status_frame, text=i18n.t("scanning_devices"), foreground="blue")
        self.lbl_bt.pack(pady=5, anchor="w")
        self.lbl_game = ttk.Label(status_frame, text=i18n.t("game_not_running"), foreground="gray")
        self.lbl_game.pack(pady=5, anchor="w")

        # Settings button
        btn_settings_frame = ttk.Frame(status_frame)
        btn_settings_frame.pack(fill="x", padx=0, pady=5)
        self.btn_settings = ttk.Button(btn_settings_frame, text="️设置 (Settings)", command=self._open_settings_window)
        self.btn_settings.pack(side=tk.LEFT, padx=5)

        # language selector
        langs = i18n.available_languages()
        if langs:
            self.lang_var = tk.StringVar(value=i18n._LANG if hasattr(i18n, '_LANG') else langs[0])
            lang_frame = ttk.Frame(status_frame)
            lang_frame.pack(fill="x", pady=2)
            ttk.Label(lang_frame, text=i18n.t("language_label")).pack(side=tk.LEFT, padx=(0,5))
            self.lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=langs, state="readonly", width=8)
            self.lang_combo.pack(side=tk.LEFT)
            self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_language_change())

        wave_routine_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("wave_routine_frame_title"))
        wave_routine_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(wave_routine_frame, text=i18n.t("select_wave_label")).pack(anchor="w", padx=5, pady=2)
        all_routine_options = list(WAVEFORMS.keys()) + list(WAVEFORM_SEQUENCES.keys())
        self.var_routine_wave = tk.StringVar(value=self.routine_pattern_name)
        self.wave_routine_combo = ttk.Combobox(wave_routine_frame, textvariable=self.var_routine_wave, values=all_routine_options, state="readonly")
        self.wave_routine_combo.pack(fill="x", padx=5, pady=5)
        self.wave_routine_combo.bind("<<ComboboxSelected>>", self._change_routine_selection)

        repeat_frame = ttk.Frame(wave_routine_frame)
        repeat_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(repeat_frame, text=i18n.t("repeat_label")).pack(side=tk.LEFT, anchor="w")

        self.var_repeat_count_str = tk.StringVar(value=str(self.var_repeat_count.get()))
        repeat_entry = ttk.Entry(repeat_frame, textvariable=self.var_repeat_count_str, width=5)
        repeat_entry.pack(side=tk.RIGHT)
        repeat_entry.bind("<Return>", lambda event: self._validate_repeat_count())
        repeat_entry.bind("<FocusOut>", lambda event: self._validate_repeat_count())

        speed_frame = ttk.Frame(wave_routine_frame)
        speed_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(speed_frame, text=i18n.t("speed_label")).pack(side=tk.LEFT, anchor="w")

        self.var_interval_str = tk.StringVar(value=str(self.var_playback_interval.get()))
        interval_entry = ttk.Entry(speed_frame, textvariable=self.var_interval_str, width=5)
        interval_entry.pack(side=tk.RIGHT)
        interval_entry.bind("<Return>", lambda event: self._validate_interval())
        interval_entry.bind("<FocusOut>", lambda event: self._validate_interval())

        ttk.Scale(wave_routine_frame, from_=50, to=1000, variable=self.var_playback_interval, orient="horizontal").pack(fill="x", padx=5, pady=0)
        self.var_playback_interval.trace_add("write", lambda *args: self.var_interval_str.set(self.var_playback_interval.get()))

        wave_combo_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("wave_combo_frame_title"))
        wave_combo_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(wave_combo_frame, text=i18n.t("combo_label")).pack(anchor="w", padx=5, pady=2)
        self.var_combo_wave = tk.StringVar(value=self.combo_pattern_name)
        self.wave_combo_combo = ttk.Combobox(wave_combo_frame, textvariable=self.var_combo_wave, values=list(WAVEFORMS.keys()), state="readonly")
        self.wave_combo_combo.pack(fill="x", padx=5, pady=5)
        self.wave_combo_combo.bind("<<ComboboxSelected>>", self._change_combo_waveform)

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        ctrl_a_routine_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("ctrl_a_routine_frame_title"))
        ctrl_a_routine_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_a_routine_frame, "A", self.var_routine_min_a, self.var_routine_max_a)

        ctrl_b_routine_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("ctrl_b_routine_frame_title"))
        ctrl_b_routine_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_b_routine_frame, "B", self.var_routine_min_b, self.var_routine_max_b)

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        ctrl_a_combo_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("ctrl_a_combo_frame_title"))
        ctrl_a_combo_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_a_combo_frame, "A-Combo", self.var_combo_min_a, self.var_combo_max_a)

        ctrl_b_combo_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("ctrl_b_combo_frame_title"))
        ctrl_b_combo_frame.pack(fill="x", padx=10, pady=5)
        self._add_intensity_controls(ctrl_b_combo_frame, "B-Combo", self.var_combo_min_b, self.var_combo_max_b)

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        score_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("score_frame_title"))
        score_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(score_frame, text=i18n.t("score_limit_label")).pack(anchor="w", padx=5)
        ttk.Scale(score_frame, from_=100, to=2000, variable=self.var_score_limit, orient="horizontal").pack(fill="x", padx=5, pady=5)
        ttk.Label(score_frame, textvariable=self.var_score_limit).pack()

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        channel_frame = ttk.LabelFrame(scrollable_right_frame, text=i18n.t("channel_frame_title"))
        channel_frame.pack(fill="x", padx=10, pady=5)
        self.var_ch_a = tk.BooleanVar(value=True)
        self.var_ch_b = tk.BooleanVar(value=True)
        self.var_ch_a.trace_add("write", lambda *args: self._update_channels())
        self.var_ch_b.trace_add("write", lambda *args: self._update_channels())
        ttk.Checkbutton(channel_frame, text=i18n.t("channel_a_label"), variable=self.var_ch_a).pack(anchor="w", padx=5)
        ttk.Checkbutton(channel_frame, text=i18n.t("channel_b_label"), variable=self.var_ch_b).pack(anchor="w", padx=5)

        # Output display frame with fixed height
        output_frame = ttk.LabelFrame(scrollable_right_frame, text="输出状态 (Output Status)", height=100)
        output_frame.pack(pady=10, padx=10, fill="x")
        output_frame.pack_propagate(False)  # Prevent frame from shrinking/expanding
        
        self.lbl_output_a = ttk.Label(output_frame, text="A: 0%", font=("Arial", 12, "bold"), foreground="#cc0000")
        self.lbl_output_a.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.lbl_output_b = ttk.Label(output_frame, text="B: 0%", font=("Arial", 12, "bold"), foreground="#cc0000")
        self.lbl_output_b.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.lbl_output_freq = ttk.Label(output_frame, text="频率 (Freq): -- Hz", font=("Arial", 10))
        self.lbl_output_freq.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.lbl_output_mode = ttk.Label(output_frame, text="模式 (Mode): 停止 (Stop)", font=("Arial", 10))
        self.lbl_output_mode.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        output_frame.columnconfigure(0, weight=1)
        
        self.btn_run = ttk.Button(scrollable_right_frame, text=i18n.t("run_button"), command=self.run_game)
        self.btn_run.pack(pady=10, fill='x', padx=20)

    def _load_current_routine(self):
        current_pattern_name = self.routine_pattern_name

        if self.is_sequence_mode:
            sequence_list = WAVEFORM_SEQUENCES.get(self.routine_pattern_name)
            if not sequence_list:
                self.log_msg(i18n.t("sequence_not_found", name=self.routine_pattern_name), is_game_log=True)
                self.is_sequence_mode = False
                self.routine_pattern_name = "呼吸 (Breathe)"
                current_pattern_name = "呼吸 (Breathe)"
            else:
                self.sequence_pattern_index %= len(sequence_list)
                current_pattern_name = sequence_list[self.sequence_pattern_index]

            self.routine_steps = WAVEFORMS.get(current_pattern_name, WAVEFORMS["呼吸 (Breathe)"])
            self.log_msg(i18n.t("sequence_playback_switch", name=current_pattern_name), is_game_log=False)
        else:
            self.routine_steps = WAVEFORMS.get(self.routine_pattern_name, WAVEFORMS["呼吸 (Breathe)"])

        self.routine_step_index = 0

    def _change_routine_selection(self, event=None):
        new_name = self.var_routine_wave.get()
        self.routine_pattern_name = new_name

        if new_name in WAVEFORM_SEQUENCES:
            self.is_sequence_mode = True
            self.sequence_pattern_index = 0
            self.log_msg(i18n.t("mode_switch_sequence", name=new_name), is_game_log=True)
        else:
            self.is_sequence_mode = False
            self.log_msg(i18n.t("mode_switch_waveform", name=new_name), is_game_log=True)

        self.current_pattern_repeat_count = 0
        self._load_current_routine()

        if self.shock_enabled and not self.is_overriding:
            self._start_pattern_player()

    def _change_combo_waveform(self, event=None):
        new_name = self.var_combo_wave.get()
        self.combo_pattern_name = new_name
        self.combo_steps = WAVEFORMS.get(new_name, WAVEFORMS["纯脉冲 (瞬时触发)"])
        self.log_msg(i18n.t("combo_waveform_switch", name=new_name))

    def _start_pattern_player(self):
        if self.pattern_timer:
            self.root.after_cancel(self.pattern_timer)

        self.current_pattern_repeat_count = 0
        self._load_current_routine()
        self.log_msg(i18n.t("start_player", name=self.routine_pattern_name), is_game_log=True)
        self._next_pattern_step()

    def _stop_pattern_player(self):
        if self.pattern_timer:
            self.root.after_cancel(self.pattern_timer)
            self.pattern_timer = None
        self.log_msg(i18n.t("stop_pattern_player"), is_game_log=True)

    def _next_pattern_step(self):
        if self.is_overriding:
            interval_ms = self.var_playback_interval.get()
            self.pattern_timer = self.root.after(interval_ms, self._next_pattern_step)
            return

        step_data = self.routine_steps[self.routine_step_index]
        wave_freq_raw, wave_int_raw = step_data

        min_a, max_a = self.var_routine_min_a.get(), self.var_routine_max_a.get()
        scaled_intensity_a = (wave_int_raw / 100) * (max_a - min_a)
        final_intensity_a = int(min_a + scaled_intensity_a)
        final_intensity_a = min(100, max(0, final_intensity_a))

        min_b, max_b = self.var_routine_min_b.get(), self.var_routine_max_b.get()
        scaled_intensity_b = (wave_int_raw / 100) * (max_b - min_b)
        final_intensity_b = int(min_b + scaled_intensity_b)
        final_intensity_b = min(100, max(0, final_intensity_b))

        self.bt_ctrl.set_shock_split_wave(wave_freq_raw, final_intensity_a, final_intensity_b)

        current_pattern_name = self.var_routine_wave.get()
        if self.is_sequence_mode:
            current_pattern_name = WAVEFORM_SEQUENCES[self.routine_pattern_name][self.sequence_pattern_index]

        self.lbl_output_a.config(text=f"A: {final_intensity_a}%", foreground="#cc0000")
        self.lbl_output_b.config(text=f"B: {final_intensity_b}%", foreground="#cc0000")
        self.lbl_output_freq.config(text=f"频率 (Freq): {wave_freq_raw} Hz")
        self.lbl_output_mode.config(text=f"模式 (Mode): {current_pattern_name}")

        self.routine_step_index += 1

        if self.routine_step_index >= len(self.routine_steps):
            self.current_pattern_repeat_count += 1
            repeat_limit = self.var_repeat_count.get()

            if self.is_sequence_mode and self.current_pattern_repeat_count >= repeat_limit:
                self.sequence_pattern_index += 1
                self.current_pattern_repeat_count = 0
                self._load_current_routine()
            else:
                self.routine_step_index = 0

                if self.is_sequence_mode:
                    self.log_msg(i18n.t("sequence_repeat_count", name=current_pattern_name, current=self.current_pattern_repeat_count, limit=repeat_limit), is_game_log=False)

        interval_ms = self.var_playback_interval.get()
        self.pattern_timer = self.root.after(interval_ms, self._next_pattern_step)

    def _trigger_shock(self, score):
        if not self.shock_enabled:
            return

        self.is_overriding = True
        self.combo_step_index = 0

        if self.shock_override_timer:
            self.root.after_cancel(self.shock_override_timer)

        self.log_msg(i18n.t("combo_triggered", name=self.combo_pattern_name), is_game_log=True)

        self._play_combo_step(score)

    def _play_combo_step(self, trigger_score):
        if not self.is_overriding or self.combo_step_index >= COMBO_DURATION_STEPS:
            self.is_overriding = False
            self.shock_override_timer = None
            self.log_msg(i18n.t("combo_ended"), is_game_log=True)
            self.root.after(0, self._next_pattern_step)
            return

        limit = self.var_score_limit.get()
        score_multiplier = min(trigger_score / limit, 1.0)

        step_data = self.combo_steps[self.combo_step_index % len(self.combo_steps)]
        wave_freq_raw, wave_int_raw = step_data

        min_a, max_a = self.var_combo_min_a.get(), self.var_combo_max_a.get()
        scaled_base_a = (wave_int_raw / 100) * (max_a - min_a)
        final_intensity_a = int(min_a + (scaled_base_a * score_multiplier))
        final_intensity_a = min(100, max(0, final_intensity_a))

        min_b, max_b = self.var_combo_min_b.get(), self.var_combo_max_b.get()
        scaled_base_b = (wave_int_raw / 100) * (max_b - min_b)
        final_intensity_b = int(min_b + (scaled_base_b * score_multiplier))
        final_intensity_b = min(100, max(0, final_intensity_b))

        self.bt_ctrl.set_shock_split_wave(wave_freq_raw, final_intensity_a, final_intensity_b)
        self.lbl_output_a.config(text=f"A: {final_intensity_a}%", foreground="#00aaff")
        self.lbl_output_b.config(text=f"B: {final_intensity_b}%", foreground="#00aaff")
        self.lbl_output_freq.config(text=f"频率 (Freq): {wave_freq_raw} Hz")
        self.lbl_output_mode.config(text=f"模式 (Mode): Combo (倍数: {score_multiplier:.2f})")

        self.combo_step_index += 1
        self.shock_override_timer = self.root.after(100, lambda: self._play_combo_step(trigger_score))

    def _write_log(self, widget, line, is_game_log):
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
        while not self.debug_queue.empty():
            line = self.debug_queue.get_nowait()
            self._write_log(self.log_dglab_text, line, is_game_log=False)
        self.root.after(50, self.consume_debugs)

    def consume_logs(self):
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self._write_log(self.log_game_text, line, is_game_log=True)
            self._parse_logic(line)

        self.root.after(20, self.consume_logs)

    def log_msg(self, msg, is_game_log=False):
        if not self.var_log_visible.get() and not is_game_log:
            return

        log_widget = self.log_game_text if is_game_log else self.log_dglab_text

        def update():
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
            self.log_msg(i18n.t("no_channel_selected"), is_game_log=False)
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self.bt_ctrl.set_channels(False, False)
        else:
            self.bt_ctrl.set_channels(a_active, b_active)
            self.log_msg(i18n.t("channel_update", a=a_active, b=b_active), is_game_log=False)
            if self.shock_enabled and not self.is_overriding: self._start_pattern_player()

    def update_bt_status(self, msg):
        self.root.after(0, lambda: self.lbl_bt.config(text=msg))

    def _on_language_change(self):
        try:
            code = self.lang_var.get()
            i18n.set_language(code)
        except Exception:
            return
        self._apply_translations()

    def _apply_translations(self):
        try:
            self.root.title(i18n.t("app_title"))
            # update toggle text
            if self.var_log_visible.get():
                self.btn_log_toggle.config(text=i18n.t("hide_log"))
            else:
                self.btn_log_toggle.config(text=i18n.t("show_log"))
            # update run button
            self.btn_run.config(text=i18n.t("run_button"))
            # update BT label default text
            self.lbl_bt.config(text=i18n.t("scanning_devices"))
        except Exception:
            pass

    def run_game(self):
        game_path = self.game_path if os.path.isabs(self.game_path) else os.path.join(os.getcwd(), self.game_path)
        if not os.path.exists(game_path):
            self.log_msg(i18n.t("cannot_find_exe", path=game_path))
            return
        self.btn_run.config(state="disabled", text=i18n.t("game_running"))
        self.lbl_game.config(text=i18n.t("game_running_status"), foreground="orange")
        self.log_msg(i18n.t("game_startup", path=self.game_path), is_game_log=True)
        t = threading.Thread(target=self._process_thread, args=([game_path],), daemon=True)
        t.start()

    def _process_thread(self, cmd_list):
        try:
            process = subprocess.Popen(
                cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, text=True, bufsize=1, errors='replace'
            )
            self.game_process = process

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None: break
                if line: self.log_queue.put(line.strip())

            self.log_queue.put(i18n.t("game_closed"))

        except Exception as e:
            self.log_queue.put(i18n.t("startup_exception", err=str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal", text=i18n.t("run_button")))
            self.root.after(0, lambda: self.lbl_game.config(text=i18n.t("game_stopped"), foreground="red"))
            self.shock_enabled = False
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self._stop_pattern_player()

    def _parse_logic(self, line):
        if "[Beats] Crossfade 0 -> 0" in line:
            self.shock_enabled = True
            self.lbl_game.config(text=i18n.t("game_running_shock_enabled"), foreground="green")
            self.log_msg(i18n.t("game_start_detected"), is_game_log=True)
            self._start_pattern_player()
        elif "Writing player records" in line:
            self.shock_enabled = False
            self.lbl_game.config(text=i18n.t("game_settlement_status"), foreground="blue")
            self.bt_ctrl.set_shock_split_wave(10, 0, 0)
            self._stop_pattern_player()
            self.lbl_output_a.config(text="A: 0%", foreground="#cc0000")
            self.lbl_output_b.config(text="B: 0%", foreground="#cc0000")
            self.lbl_output_freq.config(text="频率 (Freq): -- Hz")
            self.lbl_output_mode.config(text="模式 (Mode): 停止 (Stop)")
            self.log_msg(i18n.t("game_end_detected"), is_game_log=True)
        elif "[Chain] TOTAL SCORE:" in line:
            match = re.search(r"TOTAL SCORE:\s+(\d+)", line)
            if match and self.shock_enabled:
                score = int(match.group(1))
                self._trigger_shock(score)

    def _on_window_close(self):
        """Save configuration and close window."""
        self.config["language"] = self.lang_var.get() if hasattr(self, 'lang_var') else i18n._LANG
        self.config["game_path"] = self.game_path
        self.config["routine_min_a"] = self.var_routine_min_a.get()
        self.config["routine_max_a"] = self.var_routine_max_a.get()
        self.config["routine_min_b"] = self.var_routine_min_b.get()
        self.config["routine_max_b"] = self.var_routine_max_b.get()
        self.config["combo_min_a"] = self.var_combo_min_a.get()
        self.config["combo_max_a"] = self.var_combo_max_a.get()
        self.config["combo_min_b"] = self.var_combo_min_b.get()
        self.config["combo_max_b"] = self.var_combo_max_b.get()
        self.config["score_limit"] = self.var_score_limit.get()
        self.config["playback_interval"] = self.var_playback_interval.get()
        self.config["repeat_count"] = self.var_repeat_count.get()
        save_config(self.config)
        self.root.destroy()

    def _open_settings_window(self):
        """Open settings window."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("设置 / Settings")
        settings_win.geometry("450x500")
        settings_win.resizable(False, False)
        
        # Create main frame
        main_frame = ttk.Frame(settings_win, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game path setting
        ttk.Label(main_frame, text="游戏路径 (Game Path):", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.game_path_var = tk.StringVar(value=self.game_path)
        game_path_entry = ttk.Entry(main_frame, textvariable=self.game_path_var, width=40)
        game_path_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        
        def browse_game():
            path = filedialog.askopenfilename(filetypes=[("EXE files", "*.exe"), ("All files", "*.*")])
            if path:
                self.game_path_var.set(path)
                self.game_path = path
        
        ttk.Button(main_frame, text="浏览 (Browse)", command=browse_game).grid(row=1, column=1, sticky="ew")
        
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        
        # Shock intensities
        ttk.Label(main_frame, text="电击强度 / Shock Intensities", font=("Arial", 10, "bold")).grid(row=3, column=0, columnspan=2, sticky="w")
        
        # Routine A
        ttk.Label(main_frame, text="A 通道常规 (Routine A):").grid(row=4, column=0, sticky="w", pady=5)
        min_a_var = tk.IntVar(value=self.var_routine_min_a.get())
        max_a_var = tk.IntVar(value=self.var_routine_max_a.get())
        ttk.Label(main_frame, text="Min:").grid(row=5, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=min_a_var, width=10).grid(row=5, column=1, sticky="w")
        ttk.Label(main_frame, text="Max:").grid(row=6, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=max_a_var, width=10).grid(row=6, column=1, sticky="w")
        
        # Routine B
        ttk.Label(main_frame, text="B 通道常规 (Routine B):").grid(row=7, column=0, sticky="w", pady=5)
        min_b_var = tk.IntVar(value=self.var_routine_min_b.get())
        max_b_var = tk.IntVar(value=self.var_routine_max_b.get())
        ttk.Label(main_frame, text="Min:").grid(row=8, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=min_b_var, width=10).grid(row=8, column=1, sticky="w")
        ttk.Label(main_frame, text="Max:").grid(row=9, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=max_b_var, width=10).grid(row=9, column=1, sticky="w")
        
        # Combo A
        ttk.Label(main_frame, text="A 通道 Combo:").grid(row=10, column=0, sticky="w", pady=5)
        combo_min_a_var = tk.IntVar(value=self.var_combo_min_a.get())
        combo_max_a_var = tk.IntVar(value=self.var_combo_max_a.get())
        ttk.Label(main_frame, text="Min:").grid(row=11, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=combo_min_a_var, width=10).grid(row=11, column=1, sticky="w")
        ttk.Label(main_frame, text="Max:").grid(row=12, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=combo_max_a_var, width=10).grid(row=12, column=1, sticky="w")
        
        # Combo B
        ttk.Label(main_frame, text="B 通道 Combo:").grid(row=13, column=0, sticky="w", pady=5)
        combo_min_b_var = tk.IntVar(value=self.var_combo_min_b.get())
        combo_max_b_var = tk.IntVar(value=self.var_combo_max_b.get())
        ttk.Label(main_frame, text="Min:").grid(row=14, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=combo_min_b_var, width=10).grid(row=14, column=1, sticky="w")
        ttk.Label(main_frame, text="Max:").grid(row=15, column=0, sticky="e", padx=(20, 5))
        ttk.Spinbox(main_frame, from_=0, to=100, textvariable=combo_max_b_var, width=10).grid(row=15, column=1, sticky="w")
        
        ttk.Separator(main_frame, orient='horizontal').grid(row=16, column=0, columnspan=2, sticky="ew", pady=10)
        
        # Score limit
        ttk.Label(main_frame, text="分数阈值 (Score Limit):").grid(row=17, column=0, sticky="w", pady=5)
        score_var = tk.IntVar(value=self.var_score_limit.get())
        ttk.Spinbox(main_frame, from_=100, to=5000, textvariable=score_var, width=15).grid(row=17, column=1, sticky="w")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=18, column=0, columnspan=2, sticky="ew", pady=20)
        
        def save_settings():
            self.var_routine_min_a.set(min_a_var.get())
            self.var_routine_max_a.set(max_a_var.get())
            self.var_routine_min_b.set(min_b_var.get())
            self.var_routine_max_b.set(max_b_var.get())
            self.var_combo_min_a.set(combo_min_a_var.get())
            self.var_combo_max_a.set(combo_max_a_var.get())
            self.var_combo_min_b.set(combo_min_b_var.get())
            self.var_combo_max_b.set(combo_max_b_var.get())
            self.var_score_limit.set(score_var.get())
            messagebox.showinfo("✅ 成功", "设置已保存 / Settings saved!")
            settings_win.destroy()
        
        ttk.Button(button_frame, text="保存 (Save)", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭 (Close)", command=settings_win.destroy).pack(side=tk.LEFT, padx=5)
        
        # Make columns expand properly
        main_frame.columnconfigure(1, weight=1)


def run():
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        try:
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    root = tk.Tk()
    app = GameControllerApp(root)
    root.mainloop()
