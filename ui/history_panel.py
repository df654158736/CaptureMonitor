"""
History display panel for showing OCR results and changes.
Optimized for performance with incremental updates.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat
import logging

from core.monitor import HistoryEntry

logger = logging.getLogger(__name__)


class HistoryPanel(QWidget):
    """
    Independent draggable window for displaying monitoring history.
    Uses incremental updates for better performance.
    """

    # Signals
    clear_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("\u5386\u53f2\u8bb0\u5f55")
        self.setMinimumSize(400, 300)

        # Make window draggable and stay on top
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # Track loaded entries for incremental updates
        self._loaded_count = 0
        self._is_first_load = True

        # Limit displayed entries for performance
        self._max_display = 200

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title label
        title_label = QLabel("\u76d1\u63a7\u5386\u53f2")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Text area for history
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.text_edit)

        # Buttons
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("\u6e05\u7a7a")
        self.clear_btn.clicked.connect(self._on_clear)
        button_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("\u5bfc\u51fa")
        self.export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("0 \u6761\u8bb0\u5f55")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def add_entry(self, entry: HistoryEntry):
        """Add a history entry to the display (incremental update)."""
        text = str(entry)

        # Create format for entry
        format = QTextCharFormat()
        if entry.is_change:
            # Highlight changes with orange color
            format.setForeground(QColor(255, 140, 0))
            format.setFontWeight(700)  # Bold
        else:
            format.setForeground(QColor(0, 0, 0))

        # Insert text with formatting
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Add newline if not first entry
        if self.text_edit.toPlainText():
            cursor.insertText('\n')

        cursor.insertText(text, format)

        # Update loaded count
        self._loaded_count += 1

        # Auto-scroll to bottom
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

        self._update_status()

    def set_history(self, entries: list[HistoryEntry]):
        """
        Set the entire history display.
        Uses incremental update for better performance.
        Only displays the most recent entries to avoid lag.
        """
        # Limit to most recent entries for performance
        if len(entries) > self._max_display:
            entries = entries[-self._max_display:]

        if not entries:
            self.text_edit.clear()
            self._loaded_count = 0
            self._is_first_load = True
            self._update_status()
            return

        # First time: load all entries
        if self._is_first_load:
            self._load_all_entries(entries)
            self._is_first_load = False
        else:
            # Subsequent updates: only add new entries
            new_entries = entries[self._loaded_count:]
            if new_entries:
                for entry in new_entries:
                    self.add_entry(entry)

    def _load_all_entries(self, entries: list[HistoryEntry]):
        """
        Load all entries at once (first time only).
        Uses simple text for better performance.
        """
        # Build text as plain text (faster than HTML)
        text_lines = []
        for entry in entries:
            text_lines.append(str(entry))

        # Set text in one operation
        self.text_edit.setPlainText('\n'.join(text_lines))

        # Update loaded count
        self._loaded_count = len(entries)

        # Auto-scroll to bottom
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

        self._update_status()

        logger.info(f"Loaded {len(entries)} history entries")

    def clear(self):
        """Clear all entries."""
        self.text_edit.clear()
        self._loaded_count = 0
        self._is_first_load = True
        self._update_status()

    def _on_clear(self):
        """Handle clear button click."""
        self.clear()
        self.clear_requested.emit()

    def _on_export(self):
        """Handle export button click."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "\u5bfc\u51fa\u5386\u53f2",
            "monitor_history.txt",
            "\u6587\u672c\u6587\u4ef6 (*.txt);;\u6240\u6709\u6587\u4ef6 (*)"
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.status_label.setText(f"\u5df2\u5bfc\u51fa\u5230 {filepath}")
                logger.info(f"History exported to {filepath}")
            except Exception as e:
                logger.error(f"Error exporting history: {e}")
                self.status_label.setText(f"\u5bfc\u51fa\u5931\u8d25: {e}")

    def _update_status(self):
        """Update the status label."""
        self.status_label.setText(f"{self._loaded_count} \u6761\u8bb0\u5f55")

    def showEvent(self, event):
        """Handle show event - ensure cursor is at end."""
        super().showEvent(event)
        # Move cursor to end when showing
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def closeEvent(self, event):
        """Handle close event - just hide instead of close."""
        self.hide()
        event.ignore()
