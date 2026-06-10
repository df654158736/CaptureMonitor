"""译文框交互测试(Qt offscreen)。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy

import pytest
from PyQt6.QtCore import QPointF, QEvent, Qt
from PyQt6.QtGui import QMouseEvent

from core.config import DEFAULT_CONFIG


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _overlay(mode="manual"):
    from ui.translation_overlay import TranslationOverlay
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["trigger"]["mode"] = mode
    return cfg, TranslationOverlay(cfg)


def _press(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mousePressEvent(e)


def _move(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseMove, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mouseMoveEvent(e)


def _release(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mouseReleaseEvent(e)


def test_tap_emits_translate_requested(app):
    _cfg, ov = _overlay()
    ov.setGeometry(500, 500, 480, 160)
    got = []
    ov.translate_requested.connect(lambda: got.append(1))
    _press(ov, 520, 520)
    _release(ov, 520, 520)        # 原地松开 = 轻点
    assert got == [1]


def test_drag_does_not_emit_translate(app):
    _cfg, ov = _overlay()
    ov.setGeometry(500, 500, 480, 160)
    got = []
    ov.translate_requested.connect(lambda: got.append(1))
    _press(ov, 520, 520)
    _move(ov, 600, 600)           # 移动 >4px
    _release(ov, 600, 600)
    assert got == []              # 拖动不算翻译


def test_redock_button_visibility_and_action(app):
    cfg, ov = _overlay()
    ov.dock_to(100, 100, 480, 160)     # 吸附 → 按钮隐藏
    assert ov.redock_btn.isHidden()
    cfg["overlay"]["detached"] = True  # 模拟脱离
    ov.redock_btn.show()
    assert not ov.redock_btn.isHidden()
    ov.redock_btn.click()              # 归位
    assert cfg["overlay"]["detached"] is False
    assert ov.redock_btn.isHidden()


def test_set_mode_updates_placeholder(app):
    _cfg, ov = _overlay(mode="manual")
    assert ov.dst_label.text() == "点此翻译"
    ov.set_mode("auto")
    assert ov.dst_label.text() == "等待翻译…"
    ov.set_text("Hi", "你好")
    ov.set_mode("manual")              # 已有译文,占位不再覆盖
    assert ov.dst_label.text() == "你好"
