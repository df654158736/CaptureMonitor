"""
Monitor core with QTimer-based monitoring loop.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, Callable, List
from datetime import datetime
import logging
import difflib

from core.ocr.base import BaseOCREngine
from core.plugin_loader import Plugin
from core.translator import Translator
from utils.screen_capture import capture_region

logger = logging.getLogger(__name__)


class HistoryEntry:
    """Represents a single history entry."""

    def __init__(self, timestamp: datetime, plugin_name: str, content: str,
                 is_change: bool = False, translated_content: str = None):
        self.timestamp = timestamp
        self.plugin_name = plugin_name
        self.content = content
        self.is_change = is_change
        self.translated_content = translated_content

    def __str__(self):
        time_str = self.timestamp.strftime("%H:%M:%S")
        prefix = "\u26a0\ufe0f " if self.is_change else ""
        if self.translated_content:
            return f"[{time_str}] {self.plugin_name}: {prefix}{self.content}\n    [译] {self.translated_content}"
        return f"[{time_str}] {self.plugin_name}: {prefix}{self.content}"


class Monitor(QObject):
    """
    Core monitoring class that performs OCR at regular intervals
    and detects text changes.
    """

    # Signals
    text_detected = pyqtSignal(str)  # Emitted when text is detected
    change_detected = pyqtSignal(str, str)  # Emitted when change is detected (old, new)
    history_updated = pyqtSignal()  # Emitted when history is updated
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs

    def __init__(self):
        super().__init__()
        self.ocr_engine: Optional[BaseOCREngine] = None
        self.plugin: Optional[Plugin] = None
        self.translator: Translator = Translator()
        self.interval: int = 2000  # milliseconds (default 2 seconds)
        self.region: Optional[tuple] = None  # (x, y, width, height)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._previous_text: str = ""
        self._history: List[HistoryEntry] = []
        self._max_history = 1000
        self._is_running: bool = False

    def set_ocr_engine(self, engine: BaseOCREngine):
        """Set the OCR engine to use."""
        self.ocr_engine = engine
        logger.info(f"OCR engine set to: {engine.name if engine else None}")

    def set_plugin(self, plugin: Optional[Plugin]):
        """Set the active plugin."""
        self.plugin = plugin

    def set_interval(self, seconds: float):
        """Set the monitoring interval in seconds."""
        self.interval = int(seconds * 1000)  # Convert to milliseconds
        if self._is_running:
            self._timer.setInterval(self.interval)

    def set_region(self, x: int, y: int, width: int, height: int):
        """Set the region to monitor."""
        self.region = (x, y, width, height)
        logger.info(f"Region set to: ({x}, {y}) {width}x{height}")

    def start(self):
        """Start monitoring."""
        logger.info(f"Attempting to start monitoring...")
        logger.info(f"  _is_running: {self._is_running}")
        logger.info(f"  ocr_engine: {self.ocr_engine}")
        logger.info(f"  region: {self.region}")

        if self._is_running:
            logger.info("Already running, returning")
            return

        if not self.ocr_engine:
            self.error_occurred.emit("No OCR engine selected")
            logger.error("Cannot start: No OCR engine selected")
            return

        if not self.region:
            self.error_occurred.emit("No region selected")
            logger.error("Cannot start: No region selected")
            return

        self._is_running = True
        self._timer.start(self.interval)
        logger.info(f"Monitoring started with interval {self.interval}ms")

    def stop(self):
        """Stop monitoring."""
        self._is_running = False
        self._timer.stop()
        logger.info("Monitoring stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitoring is active."""
        return self._is_running

    def _tick(self):
        """Perform one monitoring tick."""
        if not self.region or not self.ocr_engine:
            return

        try:
            # Capture the region
            from PIL import Image
            image = capture_region(*self.region)

            # Perform OCR
            text = self.ocr_engine.recognize(image)

            # Process through plugin
            if self.plugin:
                processed_text = self.plugin.process_text(text)
            else:
                processed_text = text

            # Emit signal for real-time display (not recorded to history)
            self.text_detected.emit(processed_text)

            # Check for changes using similarity threshold
            # This avoids recording OCR instability as changes
            if not self._is_similar(processed_text, self._previous_text):
                if self._previous_text:  # Skip first detection
                    self._handle_change(self._previous_text, processed_text)
                self._previous_text = processed_text

        except Exception as e:
            logger.error(f"Error during monitoring tick: {e}")
            self.error_occurred.emit(str(e))

    def _is_similar(self, text1: str, text2: str, threshold: float = 0.85) -> bool:
        """
        Check if two texts are similar enough to be considered the same.
        Uses difflib.SequenceMatcher to calculate similarity ratio.

        Args:
            text1: First text
            text2: Second text
            threshold: Similarity threshold (0.0 to 1.0), default 0.85

        Returns:
            True if texts are similar enough
        """
        if not text1 and not text2:
            return True
        if not text1 or not text2:
            return False

        # Use difflib to calculate similarity
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        return similarity >= threshold

    def _handle_change(self, old: str, new: str):
        """Handle a detected change."""
        if self.plugin:
            formatted = self.plugin.format_change(old, new)
        else:
            formatted = f"{old} \u2192 {new}"

        # Add change entry to history
        self._add_history_entry(formatted, is_change=True)

        # Emit signal
        self.change_detected.emit(old, new)
        logger.info(f"Change detected: {formatted}")

    def _add_history_entry(self, content: str, is_change: bool = False):
        """Add an entry to the history."""
        plugin_name = self.plugin.name if self.plugin else "Default"

        # Translate content if translation is enabled
        translated_content = None
        if self.translator.enabled:
            translated_content = self.translator.translate(content)

        entry = HistoryEntry(
            timestamp=datetime.now(),
            plugin_name=plugin_name,
            content=content,
            is_change=is_change,
            translated_content=translated_content
        )

        self._history.append(entry)

        # Enforce history limit
        while len(self._history) > self._max_history:
            self._history.pop(0)

        self.history_updated.emit()

    def get_history(self) -> List[HistoryEntry]:
        """Get all history entries."""
        return self._history.copy()

    def clear_history(self):
        """Clear all history entries."""
        self._history.clear()
        self.history_updated.emit()

    def export_history(self, filepath: str):
        """Export history to a file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            for entry in self._history:
                f.write(str(entry) + '\n')

    def get_history_text(self) -> str:
        """Get history as formatted text."""
        return '\n'.join(str(entry) for entry in self._history)
