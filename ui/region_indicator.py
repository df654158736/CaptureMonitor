"""
Region indicator window - shows a visible border around the monitored area.
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
import logging

logger = logging.getLogger(__name__)


class RegionIndicator(QWidget):
    """
    A frameless window that displays a border around the monitored region.
    This window stays on top and shows where the monitoring is happening.
    """

    def __init__(self):
        super().__init__()

        # Window properties - frameless, always on top, transparent background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Visual properties
        self._border_color = QColor(0, 255, 0, 200)  # Green border
        self._border_width = 3
        self._label_bg_color = QColor(0, 255, 0, 180)
        self._label_text_color = QColor(0, 0, 0, 255)

        # Hide initially
        self.hide()

    def set_region(self, x: int, y: int, width: int, height: int):
        """Set the region to display the indicator around."""
        # Make the window slightly larger than the region to show the border
        padding = self._border_width
        self.setGeometry(
            x - padding,
            y - padding,
            width + (padding * 2),
            height + (padding * 2)
        )
        self._region = QRect(padding, padding, width, height)
        self.update()
        logger.info(f"Region indicator set to: ({x}, {y}) {width}x{height}")

    def paintEvent(self, event):
        """Paint the border around the region."""
        painter = QPainter(self)

        # Draw the border
        pen = QPen(self._border_color)
        pen.setWidth(self._border_width)
        painter.setPen(pen)
        painter.drawRect(self._region)

        # Draw label at top-left corner
        label_text = "\u76d1\u63a7\u4e2d"  # "监控中"
        font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
        painter.setFont(font)

        # Calculate label size
        metrics = painter.fontMetrics()
        label_width = metrics.horizontalAdvance(label_text) + 10
        label_height = metrics.height() + 4

        # Draw label background
        label_rect = QRect(
            self._region.x(),
            self._region.y() - label_height,
            label_width,
            label_height
        )
        painter.fillRect(label_rect, self._label_bg_color)

        # Draw label text
        painter.setPen(self._label_text_color)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)

        painter.end()

    def show_indicator(self):
        """Show the indicator window."""
        if hasattr(self, '_region') and self._region.isValid():
            self.show()
            logger.info("Region indicator shown")
        else:
            logger.warning("Cannot show indicator: no region set")

    def hide_indicator(self):
        """Hide the indicator window."""
        self.hide()
        logger.info("Region indicator hidden")
