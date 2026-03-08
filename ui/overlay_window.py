"""
Full-screen overlay window for region selection.
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QMouseEvent, QPaintEvent
import logging

logger = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    """
    Full-screen semi-transparent overlay window for selecting
    a screen region to monitor.
    """

    # Signals
    region_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    region_changed = pyqtSignal(int, int, int, int)   # x, y, width, height

    def __init__(self):
        super().__init__()

        # Window properties
        self.setWindowTitle("\u9009\u62e9\u76d1\u63a7\u533a\u57df")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Selection state
        self._is_selecting = False
        self._start_pos: QPoint = QPoint()
        self._current_pos: QPoint = QPoint()
        self._selection: QRect = QRect()

        # Set full screen size
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Style
        self._selection_color = QColor(0, 150, 255, 100)
        self._selection_border = QColor(0, 150, 255, 255)
        self._text_color = QColor(255, 255, 255, 255)

    def showEvent(self, event):
        """Handle show event - update to cover full screen."""
        # Get total geometry of all screens
        total_geometry = QRect()
        for screen in QApplication.screens():
            total_geometry = total_geometry.united(screen.geometry())
        self.setGeometry(total_geometry)
        super().showEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press - start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._selection = QRect()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move - update selection."""
        if self._is_selecting:
            self._current_pos = event.pos()
            self._selection = QRect(self._start_pos, self._current_pos).normalized()
            self.region_changed.emit(
                self._selection.x(),
                self._selection.y(),
                self._selection.width(),
                self._selection.height()
            )
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release - finish selection."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._current_pos = event.pos()
            self._selection = QRect(self._start_pos, self._current_pos).normalized()

            # Emit signal if selection is valid
            if self._selection.width() > 10 and self._selection.height() > 10:
                self.region_selected.emit(
                    self._selection.x(),
                    self._selection.y(),
                    self._selection.width(),
                    self._selection.height()
                )
                logger.info(f"Region selected: {self._selection}")
                # Hide overlay after selection
                self.hide()

            self.update()

    def keyPressEvent(self, event):
        """Handle key press - escape to close."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.clear_selection()

    def paintEvent(self, event: QPaintEvent):
        """Paint the overlay and selection."""
        painter = QPainter(self)

        # Fill with semi-transparent dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Draw selection if active
        if self._selection.isValid() and not self._selection.isEmpty():
            # Clear the selected area (make it fully transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self._selection, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Draw selection border
            pen = QPen(self._selection_border)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self._selection)

            # Fill selection with semi-transparent color
            painter.fillRect(self._selection, self._selection_color)

            # Draw coordinates text
            painter.setPen(self._text_color)
            font = QFont("Microsoft YaHei", 10)
            painter.setFont(font)

            coords_text = f"({self._selection.x()}, {self._selection.y()}) {self._selection.width()}x{self._selection.height()}"

            # Position text above selection if possible, otherwise below
            text_y = self._selection.y() - 25
            if text_y < 0:
                text_y = self._selection.bottom() + 5

            painter.drawText(self._selection.x(), text_y, coords_text)

        painter.end()

    def get_selection(self) -> QRect:
        """Get the current selection."""
        return self._selection

    def clear_selection(self):
        """Clear the current selection."""
        self._selection = QRect()
        self.update()
