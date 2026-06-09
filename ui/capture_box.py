"""采集框:直接拖动/缩放,其几何即采集区域。
两态:调整态(可拖动缩放) / 锁定态(细边框 + 鼠标穿透)。
"""

import logging

from PyQt6.QtWidgets import QWidget, QSizeGrip
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor

logger = logging.getLogger(__name__)


class CaptureBox(QWidget):
    geometry_changed = pyqtSignal(int, int, int, int)  # x, y, w, h(逻辑坐标)

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._locked = False
        self._drag_offset = None
        self._scale = 1.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(16, 16)

        cap = config["capture"]
        if cap["w"] > 0 and cap["h"] > 0:
            self.setGeometry(cap["x"], cap["y"], cap["w"], cap["h"])
        else:
            self.setGeometry(300, 300, 480, 120)

    def resizeEvent(self, event):
        self._grip.move(self.width() - 16, self.height() - 16)
        self._emit_geometry()
        super().resizeEvent(event)

    def moveEvent(self, event):
        self._refresh_scale()
        self._emit_geometry()
        super().moveEvent(event)

    def showEvent(self, event):
        self._refresh_scale()
        super().showEvent(event)

    def _emit_geometry(self):
        g = self.geometry()
        cap = self._config["capture"]
        cap["x"], cap["y"], cap["w"], cap["h"] = g.x(), g.y(), g.width(), g.height()
        self.geometry_changed.emit(g.x(), g.y(), g.width(), g.height())

    def _refresh_scale(self):
        handle = self.windowHandle()
        if handle and handle.screen():
            self._scale = handle.screen().devicePixelRatio()

    def current_scale(self) -> float:
        return self._scale

    def set_locked(self, locked: bool):
        """锁定态:鼠标穿透到游戏,只保留细边框标示。"""
        self._locked = locked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, locked)
        self._grip.setVisible(not locked)
        # 重新应用窗口标志后需要再次 show
        was_visible = self.isVisible()
        if was_visible:
            self.show()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._locked:
            pen = QPen(QColor(0, 200, 0, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        else:
            painter.fillRect(self.rect(), QColor(0, 150, 255, 40))
            pen = QPen(QColor(0, 150, 255, 230))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        painter.end()

    def mousePressEvent(self, event):
        if not self._locked and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
