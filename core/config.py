"""应用配置:读写 config.json,带默认值与深合并容错。"""

import json
import os
from copy import deepcopy

DEFAULT_CONFIG = {
    "backend": "youdao",  # 当前翻译引擎: youdao | volcano
    "youdao": {"app_key": "", "app_secret": ""},
    "volcano": {"access_key": "", "secret_key": "", "region": "cn-north-1"},
    "lang": {"from": "en", "to": "zh"},  # 中性语言码,各后端内部映射到自家代码
    "capture": {"x": 0, "y": 0, "w": 0, "h": 0},
    "trigger": {"mode": "auto+hotkey", "hotkey": "alt+d"},
    "detection": {"sample_interval_ms": 120, "stability_ms": 400, "change_threshold": 8},
    "overlay": {
        "dock": "below", "detached": False,
        "x": 100, "y": 100, "w": 480, "h": 160,
        "opacity": 0.85, "show_source": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return deepcopy(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_CONFIG)
    return _deep_merge(DEFAULT_CONFIG, data)


def save_config(path: str, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
