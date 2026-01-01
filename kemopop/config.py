import json
import os
from pathlib import Path


CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'settings.json')

DEFAULT_CONFIG = {
    "language": "zh-cn",
    "game_path": "kemopop.exe",
    "routine_min_a": 0,
    "routine_max_a": 2,
    "routine_min_b": 0,
    "routine_max_b": 2,
    "combo_min_a": 10,
    "combo_max_a": 30,
    "combo_min_b": 10,
    "combo_max_b": 30,
    "score_limit": 500,
    "playback_interval": 100,
    "repeat_count": 1,
}


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    _ensure_config_dir()
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
    except Exception as e:
        print(f"Failed to load config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config_dict):
    _ensure_config_dir()
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Failed to save config: {e}")
        return False


__all__ = ["load_config", "save_config", "DEFAULT_CONFIG", "CONFIG_FILE"]
