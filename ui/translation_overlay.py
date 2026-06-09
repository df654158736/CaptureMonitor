"""译文悬浮框:无边框/置顶/半透明/可拖动/可缩放。
默认 dock 在采集框正下方并跟随;用户拖动它即切为独立模式。
"""

import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizeGrip
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


def dock_rect_below(cap_x, cap_y, cap_w, cap_h, overlay_h, gap=6):
    """采集框矩形 → 译文框吸附在其正下方的矩形(宽度跟随采集框)。"""
    return (cap_x, cap_y + cap_h + gap, cap_w, overlay_h)


class TranslationOverlay(QWidget):
    detached = pyqtSignal()  # 用户拖动 → 脱离吸附

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._drag_offset = None
        self._show_source = config["overlay"].get("show_source", False)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.src_label = QLabel("")
        self.src_label.setWordWrap(True)
        self.src_label.setStyleSheet("color: #b9c0c8; font-size: 13px;")
        self.src_label.setVisible(self._show_source)
        layout.addWidget(self.src_label)

        self.dst_label = QLabel("等待翻译…")
        self.dst_label.setWordWrap(True)
        self.dst_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        layout.addWidget(self.dst_label)

        grip = QSizeGrip(self)
        layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        ov = config["overlay"]
        self.setGeometry(ov["x"], ov["y"], ov["w"], ov["h"])
        self.setWindowOpacity(ov.get("opacity", 0.85))

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setBrush(QColor(20, 22, 26, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.end()

    def set_text(self, src: str, dst: str):
        if self._show_source:
            self.src_label.setText(src)
        self.dst_label.setText(dst or "(无文字)")

    def set_show_source(self, show: bool):
        self._show_source = show
        self.src_label.setVisible(show)

    def dock_to(self, cap_x, cap_y, cap_w, cap_h):
        """被采集框调用:吸附到采集框下方(独立模式下忽略)。"""
        if self._config["overlay"].get("detached"):
            return
        x, y, w, h = dock_rect_below(cap_x, cap_y, cap_w, cap_h, self.height())
        self.setGeometry(x, y, w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            if not self._config["overlay"].get("detached"):
                self._config["overlay"]["detached"] = True
                self.detached.emit()
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        self._save_geometry()

    def _save_geometry(self):
        g = self.geometry()
        ov = self._config["overlay"]
        ov["x"], ov["y"], ov["w"], ov["h"] = g.x(), g.y(), g.width(), g.height()
