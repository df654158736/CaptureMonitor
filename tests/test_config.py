# tests/test_config.py
import json
from core.config import load_config, save_config, DEFAULT_CONFIG


def test_load_missing_returns_defaults(tmp_path):
    cfg = load_config(str(tmp_path / "nope.json"))
    assert cfg == DEFAULT_CONFIG
    assert cfg is not DEFAULT_CONFIG  # 必须是副本,不能共享引用


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "config.json")
    cfg = load_config(path)
    cfg["youdao"]["app_key"] = "abc"
    cfg["overlay"]["opacity"] = 0.5
    save_config(path, cfg)
    again = load_config(path)
    assert again["youdao"]["app_key"] == "abc"
    assert again["overlay"]["opacity"] == 0.5


def test_partial_file_merges_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"youdao": {"app_key": "x"}}), encoding="utf-8")
    cfg = load_config(str(path))
    assert cfg["youdao"]["app_key"] == "x"
    assert cfg["youdao"]["app_secret"] == ""     # 缺失字段用默认补齐
    assert cfg["lang"]["from"] == "en"           # 缺失整段用默认补齐


def test_corrupt_file_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_config(str(path)) == DEFAULT_CONFIG


def test_default_mode_is_manual():
    assert DEFAULT_CONFIG["trigger"]["mode"] == "manual"
    assert DEFAULT_CONFIG["detection"]["stable_hamming"] == 3
    assert DEFAULT_CONFIG["detection"]["change_hamming"] == 5


def test_legacy_auto_hotkey_normalized(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"trigger": {"mode": "auto+hotkey"}}), encoding="utf-8")
    assert load_config(str(path))["trigger"]["mode"] == "auto"


def test_unknown_mode_falls_back_to_manual(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"trigger": {"mode": "whatever"}}), encoding="utf-8")
    assert load_config(str(path))["trigger"]["mode"] == "manual"


def test_valid_modes_preserved(tmp_path):
    for m in ("manual", "auto"):
        path = tmp_path / f"{m}.json"
        path.write_text(json.dumps({"trigger": {"mode": m}}), encoding="utf-8")
        assert load_config(str(path))["trigger"]["mode"] == m
