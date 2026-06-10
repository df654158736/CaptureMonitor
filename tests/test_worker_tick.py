"""worker 单次循环体 _tick 的门控测试(不启动线程)。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image

from core.backends.base import TranslationResult
from core.worker import TranslationWorker


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class DummyPipeline:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def process_frame(self, frame, now, force=False, on_translating=None):
        self.calls.append(force)
        return self.result


def test_tick_manual_idle_does_not_capture(app):
    def boom():
        raise AssertionError("手动空闲不应截屏(get_region 不该被调用)")

    w = TranslationWorker(DummyPipeline(), get_region=boom,
                          get_scale=lambda: 1.0, get_auto=lambda: False, debug_dir=None)
    assert w._tick() is None  # 无 force + 非自动 → 直接返回,boom 未触发


def test_tick_force_translates_then_idles(app, monkeypatch):
    monkeypatch.setattr("core.worker.capture_region", lambda *a: Image.new("RGB", (4, 4)))
    res = TranslationResult("Hi", "你好", [])
    pipe = DummyPipeline(res)
    w = TranslationWorker(pipe, get_region=lambda: (0, 0, 10, 10),
                          get_scale=lambda: 1.0, get_auto=lambda: False, debug_dir=None)
    w.request_force()
    assert w._tick() is res          # force 截一帧翻译
    assert pipe.calls == [True]      # force 透传给管线
    assert w._tick() is None         # force 已消费,回到空闲不截屏


def test_tick_auto_captures_each_frame(app, monkeypatch):
    monkeypatch.setattr("core.worker.capture_region", lambda *a: Image.new("RGB", (4, 4)))
    pipe = DummyPipeline(None)       # 管线判定无变化
    w = TranslationWorker(pipe, get_region=lambda: (0, 0, 10, 10),
                          get_scale=lambda: 1.0, get_auto=lambda: True, debug_dir=None)
    assert w._tick() is None
    assert pipe.calls == [False]     # 自动模式:截帧并交管线,force=False
