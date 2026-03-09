"""
Monitor core with QTimer-based monitoring loop.
Runs OCR in background thread to avoid blocking UI.
Includes detailed performance logging.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker
from typing import Optional, List
from datetime import datetime
import logging
import difflib
import time

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


class OCRWorker(QThread):
    """Background worker for OCR recognition with performance tracking."""

    finished = pyqtSignal(str, float)  # Emits recognized text and elapsed time

    def __init__(self, ocr_engine, image, region):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.image = image
        self.region = region

    def run(self):
        """Perform OCR in background thread with timing."""
        start_time = time.time()
        try:
            text = self.ocr_engine.recognize(self.image)
            elapsed = time.time() - start_time
            self.finished.emit(text, elapsed)
            logger.debug(f"OCR completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"OCR worker error after {elapsed:.3f}s: {e}")
            self.finished.emit("", elapsed)


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

        # Thread safety
        self._mutex = QMutex()
        self._is_processing = False

        # Performance tracking
        self._ocr_times: List[float] = []
        self._translation_times: List[float] = []
        self._max_samples = 10  # Keep last N samples for averaging

    def set_ocr_engine(self, engine: BaseOCREngine):
        """Set the OCR engine to use."""
        self.ocr_engine = engine
        logger.info(f"OCR engine set to: {engine.name if engine else None}")
        # Reset performance stats when engine changes
        self._ocr_times.clear()

    def set_plugin(self, plugin: Optional[Plugin]):
        """Set the active plugin."""
        self.plugin = plugin
        logger.info(f"Plugin set to: {plugin.name if plugin else None}")

    def set_interval(self, seconds: float):
        """Set the monitoring interval in seconds."""
        old_interval = self.interval
        self.interval = int(seconds * 1000)  # Convert to milliseconds
        if self._is_running:
            self._timer.setInterval(self.interval)
        logger.info(f"Monitoring interval changed from {old_interval}ms to {self.interval}ms")

    def set_region(self, x: int, y: int, width: int, height: int):
        """Set the region to monitor."""
        self.region = (x, y, width, height)
        logger.info(f"Region set to: ({x}, {y}) {width}x{height}")

    def start(self):
        """Start monitoring."""
        logger.info("=" * 60)
        logger.info("Starting monitoring...")
        logger.info(f"  OCR engine: {self.ocr_engine.name if self.ocr_engine else None}")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Interval: {self.interval}ms ({self.interval/1000:.1f}s)")
        logger.info(f"  Plugin: {self.plugin.name if self.plugin else None}")
        logger.info(f"  Translation: {'enabled' if self.translator.enabled else 'disabled'}")
        logger.info("=" * 60)

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
        logger.info(f"[OK] Monitoring started")

    def stop(self):
        """Stop monitoring."""
        self._is_running = False
        self._timer.stop()
        self._log_performance_summary()
        logger.info("[OK] Monitoring stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitoring is active."""
        return self._is_running

    def _tick(self):
        """Perform one monitoring tick."""
        if not self.region or not self.ocr_engine:
            return

        # Skip if still processing previous OCR
        with QMutexLocker(self._mutex):
            if self._is_processing:
                logger.debug("[WAIT] Previous OCR still processing, skipping this tick")
                return
            self._is_processing = True

        tick_start = time.time()
        logger.debug(f"[CHANGE] Tick started at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

        try:
            # Capture the region
            capture_start = time.time()
            from PIL import Image
            image = capture_region(*self.region)
            capture_time = time.time() - capture_start
            logger.debug(f"[CAPTURE] Screenshot captured: {capture_time*1000:.1f}ms")

            # Perform OCR in background thread
            self._ocr_worker = OCRWorker(self.ocr_engine, image, self.region)
            self._ocr_worker.finished.connect(
                lambda text, ocr_time: self._on_ocr_complete(
                    text, image, tick_start, capture_time, ocr_time
                )
            )
            self._ocr_worker.start()

        except Exception as e:
            tick_time = time.time() - tick_start
            logger.error(f"[ERROR] Error during monitoring tick ({tick_time:.3f}s): {e}")
            self.error_occurred.emit(str(e))
            with QMutexLocker(self._mutex):
                self._is_processing = False

    def _on_ocr_complete(self, text: str, image, tick_start: float, capture_time: float, ocr_time: float):
        """Handle OCR completion from background thread."""
        try:
            # Record OCR time
            self._ocr_times.append(ocr_time)
            if len(self._ocr_times) > self._max_samples:
                self._ocr_times.pop(0)

            avg_ocr_time = sum(self._ocr_times) / len(self._ocr_times)

            # Log OCR result with timing
            text_preview = text[:50] + "..." if len(text) > 50 else text
            logger.info(f"[OCR] OCR: {ocr_time:.3f}s (avg: {avg_ocr_time:.3f}s) | Text: \"{text_preview}\"")

            # Process through plugin
            process_start = time.time()
            if self.plugin:
                processed_text = self.plugin.process_text(text)
            else:
                processed_text = text
            process_time = time.time() - process_start
            logger.debug(f"[PLUGIN] Plugin processing: {process_time*1000:.1f}ms")

            # Emit signal for real-time display (not recorded to history)
            self.text_detected.emit(processed_text)

            # Check for changes using similarity threshold
            # This avoids recording OCR instability as changes
            if not self._is_similar(processed_text, self._previous_text):
                if self._previous_text:  # Skip first detection
                    self._handle_change(self._previous_text, processed_text)
                self._previous_text = processed_text

            # Log total tick time
            tick_time = time.time() - tick_start
            logger.debug(f"[OK] Tick completed: {tick_time:.3f}s (screenshot: {capture_time:.3f}s, OCR: {ocr_time:.3f}s)")

        except Exception as e:
            logger.error(f"[ERROR] Error processing OCR result: {e}")
            self.error_occurred.emit(str(e))
        finally:
            # Reset processing flag
            with QMutexLocker(self._mutex):
                self._is_processing = False

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
        logger.debug(f"[SIMILARITY] Similarity: {similarity:.2%} (threshold: {threshold:.2%})")
        return similarity >= threshold

    def _handle_change(self, old: str, new: str):
        """Handle a detected change."""
        logger.info(f"[CHANGE] Change detected: \"{old[:30]}...\" → \"{new[:30]}...\"")

        if self.plugin:
            formatted = self.plugin.format_change(old, new)
        else:
            formatted = f"{old} \u2192 {new}"

        # Add change entry to history
        self._add_history_entry(formatted, is_change=True)

        # Emit signal
        self.change_detected.emit(old, new)

    def _add_history_entry(self, content: str, is_change: bool = False):
        """Add an entry to the history with timing info."""
        plugin_name = self.plugin.name if self.plugin else "Default"

        # Translate content if translation is enabled (with timeout protection)
        translated_content = None
        if self.translator.enabled:
            translate_start = time.time()
            logger.debug(f"[TRANSLATE] Translating: \"{content[:50]}...\"")

            translated_content = self.translator.translate(content)

            translate_time = time.time() - translate_start

            # Record translation time
            self._translation_times.append(translate_time)
            if len(self._translation_times) > self._max_samples:
                self._translation_times.pop(0)

            avg_translate_time = sum(self._translation_times) / len(self._translation_times)

            if translated_content != content:
                logger.info(f"[TRANSLATE] Translation: {translate_time:.3f}s (avg: {avg_translate_time:.3f}s) | Result: \"{translated_content[:30]}...\"")
            else:
                logger.debug(f"[TRANSLATE] Translation skipped/failed: {translate_time:.3f}s")

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

    def _log_performance_summary(self):
        """Log performance summary when stopping."""
        logger.info("=" * 60)
        logger.info("Performance Summary")

        if self._ocr_times:
            avg_ocr = sum(self._ocr_times) / len(self._ocr_times)
            min_ocr = min(self._ocr_times)
            max_ocr = max(self._ocr_times)
            logger.info(f"OCR ({len(self._ocr_times)} samples):")
            logger.info(f"  Average: {avg_ocr:.3f}s")
            logger.info(f"  Min: {min_ocr:.3f}s")
            logger.info(f"  Max: {max_ocr:.3f}s")

        if self._translation_times:
            avg_trans = sum(self._translation_times) / len(self._translation_times)
            min_trans = min(self._translation_times)
            max_trans = max(self._translation_times)
            logger.info(f"Translation ({len(self._translation_times)} samples):")
            logger.info(f"  Average: {avg_trans:.3f}s")
            logger.info(f"  Min: {min_trans:.3f}s")
            logger.info(f"  Max: {max_trans:.3f}s")

        logger.info(f"History entries: {len(self._history)}")
        logger.info("=" * 60)

    def get_history(self) -> List[HistoryEntry]:
        """Get all history entries."""
        with QMutexLocker(self._mutex):
            return self._history.copy()

    def clear_history(self):
        """Clear all history entries."""
        with QMutexLocker(self._mutex):
            self._history.clear()
        self.history_updated.emit()
        logger.info("[DELETE] History cleared")

    def export_history(self, filepath: str):
        """Export history to a file."""
        with QMutexLocker(self._mutex):
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self._history:
                    f.write(str(entry) + '\n')
        logger.info(f"[EXPORT] History exported to {filepath}")

    def get_history_text(self) -> str:
        """Get history as formatted text."""
        with QMutexLocker(self._mutex):
            return '\n'.join(str(entry) for entry in self._history)
