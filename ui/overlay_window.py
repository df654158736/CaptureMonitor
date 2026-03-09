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

        # Store the offset for coordinate conversion (in case window starts from negative coordinates)
        self._offset_x = 0
        self._offset_y = 0

        # Set full screen size
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Style
        self._selection_color = QColor(0, 150, 255, 100)
        self._selection_border = QColor(0, 150, 255, 255)
        self._text_color = QColor(255, 255, 255, 255)

    def showEvent(self, event):
        """Handle show event - update to cover all screens."""
        # Get total geometry of all screens (including negative coordinates)
        min_x = 0
        min_y = 0
        max_x = 0
        max_y = 0

        for screen in QApplication.screens():
            geo = screen.geometry()
            min_x = min(min_x, geo.x())
            min_y = min(min_y, geo.y())
            max_x = max(max_x, geo.x() + geo.width())
            max_y = max(max_y, geo.y() + geo.height())

        # Store offset for coordinate conversion
        self._offset_x = min_x
        self._offset_y = min_y

        # Set geometry to cover all screens
        total_width = max_x - min_x
        total_height = max_y - min_y
        self.setGeometry(min_x, min_y, total_width, total_height)

        logger.info(f"Overlay covering: ({min_x}, {min_y}) {total_width}x{total_height}")
        logger.info(f"Offset: ({self._offset_x}, {self._offset_y})")
        super().showEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press - start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_selecting = True
            # Convert window coordinates to screen coordinates
            screen_x = event.pos().x() + self._offset_x
            screen_y = event.pos().y() + self._offset_y
            self._start_pos = QPoint(screen_x, screen_y)
            self._current_pos = QPoint(screen_x, screen_y)
            self._selection = QRect()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move - update selection."""
        if self._is_selecting:
            # Convert window coordinates to screen coordinates
            screen_x = event.pos().x() + self._offset_x
            screen_y = event.pos().y() + self._offset_y
            self._current_pos = QPoint(screen_x, screen_y)
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
            # Convert window coordinates to screen coordinates
            screen_x = event.pos().x() + self._offset_x
            screen_y = event.pos().y() + self._offset_y
            self._current_pos = QPoint(screen_x, screen_y)
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
            # Convert screen coordinates to window coordinates for drawing
            window_selection = QRect(
                self._selection.x() - self._offset_x,
                self._selection.y() - self._offset_y,
                self._selection.width(),
                self._selection.height()
            )

            # Clear the selected area (make it fully transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(window_selection, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # Draw selection border
            pen = QPen(self._selection_border)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(window_selection)

            # Fill selection with semi-transparent color
            painter.fillRect(window_selection, self._selection_color)

            # Draw coordinates text
            painter.setPen(self._text_color)
            font = QFont("Microsoft YaHei", 10)
            painter.setFont(font)

            coords_text = f"({self._selection.x()}, {self._selection.y()}) {self._selection.width()}x{self._selection.height()}"

            # Position text above selection if possible, otherwise below
            text_y = window_selection.y() - 25
            if text_y < 0:
                text_y = window_selection.bottom() + 5

            painter.drawText(window_selection.x(), text_y, coords_text)

        painter.end()

    def get_selection(self) -> QRect:
        """Get the current selection."""
        return self._selection

    def clear_selection(self):
        """Clear the current selection."""
        self._selection = QRect()
        self.update()
