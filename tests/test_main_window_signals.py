"""MainWindow 信号行为测试(Qt offscreen,无需真实显示)。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy

import pytest

from core.config import DEFAULT_CONFIG


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    instance = QApplication.instance() or QApplication([])
    yield instance


def test_capture_toggle_emits_show_then_hide(app):
    """显示采集框 → 再点一次应触发隐藏(Bug: 之前隐藏无信号)。"""
    from ui.main_window import MainWindow

    window = MainWindow(copy.deepcopy(DEFAULT_CONFIG))
    shown, hidden = [], []
    window.show_capture_requested.connect(lambda: shown.append(1))
    window.hide_capture_requested.connect(lambda: hidden.append(1))

    window.capture_btn.setChecked(True)   # 显示
    window.capture_btn.setChecked(False)  # 隐藏

    assert shown == [1]
    assert hidden == [1]
