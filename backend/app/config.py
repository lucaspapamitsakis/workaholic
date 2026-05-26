import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

DEFAULT_CONFIG = {
    "obsidian_vault_path": "",
    "notes_subfolder": "",
    "visualization_session_count": 4,
    "default_weight_increment_lbs": 5.0,
    "default_reps_increment": 2,
    "default_duration_increment_sec": 5.0,
    # Pace progression: 0.005 sec/m == 2.5 sec/500m faster, a meaningful
    # but achievable improvement target for rowing/running/cardio.
    "default_pace_increment_sec_per_m": 0.005,
    "consolidation_threshold": 3,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        # Merge with defaults for any missing keys
        for key, value in DEFAULT_CONFIG.items():
            config.setdefault(key, value)
        return config
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
