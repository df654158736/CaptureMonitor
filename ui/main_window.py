"""
Main control window for the CaptureMonitor application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox,
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional
import logging

from core.ocr.base import BaseOCREngine
from core.ocr.paddle_ocr import PaddleOCREngine
from core.ocr.windows_ocr import WindowsOCREngine
from core.ocr.tesseract_ocr import TesseractOCREngine
from core.plugin_loader import Plugin
from core.monitor import Monitor

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main control window for the application."""

    # Signals
    show_overlay_requested = pyqtSignal()
    hide_overlay_requested = pyqtSignal()
    start_monitoring_requested = pyqtSignal()
    stop_monitoring_requested = pyqtSignal()
    clear_history_requested = pyqtSignal()
    ocr_changed = pyqtSignal(object)  # BaseOCREngine
    plugin_changed = pyqtSignal(object)  # Optional[Plugin]
    interval_changed = pyqtSignal(float)  # seconds

    def __init__(self):
        super().__init__()
        self.setWindowTitle("\u5c4f\u5e55\u6587\u5b57\u76d1\u63a7\u5de5\u5177")
        self.setMinimumSize(400, 300)

        self.plugins: List[Plugin] = []
        self.current_ocr: Optional[BaseOCREngine] = None
        self.current_plugin: Optional[Plugin] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # OCR Engine Selection
        ocr_group = QGroupBox("OCR \u5f15\u64ce")
        ocr_layout = QVBoxLayout(ocr_group)

        self.ocr_combo = QComboBox()
        self.ocr_combo.addItem("Tesseract OCR (推荐)", "tesseract")
        self.ocr_combo.addItem("PaddleOCR (实验性)", "paddle")
        self.ocr_combo.addItem("Windows OCR", "windows")
        self.ocr_combo.currentIndexChanged.connect(self._on_ocr_changed)
        ocr_layout.addWidget(self.ocr_combo)

        layout.addWidget(ocr_group)

        # Plugin Selection
        plugin_group = QGroupBox("\u63d2\u4ef6")
        plugin_layout = QVBoxLayout(plugin_group)

        self.plugin_combo = QComboBox()
        self.plugin_combo.currentIndexChanged.connect(self._on_plugin_changed)
        plugin_layout.addWidget(self.plugin_combo)

        layout.addWidget(plugin_group)

        # Interval Setting
        interval_group = QGroupBox("\u76d1\u63a7\u95f4\u9694")
        interval_layout = QHBoxLayout(interval_group)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(2)
        self.interval_spin.setSuffix(" \u79d2")
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        interval_layout.addWidget(self.interval_spin)

        layout.addWidget(interval_group)

        # Control Buttons
        control_group = QGroupBox("\u63a7\u5236")
        control_layout = QVBoxLayout(control_group)

        # Overlay button
        self.overlay_btn = QPushButton("\u663e\u793a\u76d1\u63a7\u6846\u67b6")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.toggled.connect(self._on_overlay_toggled)
        control_layout.addWidget(self.overlay_btn)

        # Start/Stop buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("\u5f00\u59cb\u76d1\u63a7")
        self.start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("\u505c\u6b62\u76d1\u63a7")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        control_layout.addLayout(btn_layout)

        # Clear history button
        self.clear_btn = QPushButton("\u6e05\u7a7a\u5386\u53f2")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        control_layout.addWidget(self.clear_btn)

        layout.addWidget(control_group)

        # Status
        self.status_label = QLabel("\u5c31\u7eea - \u8bf7\u9009\u62e9\u76d1\u63a7\u533a\u57df")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        # Add stretch to push everything up
        layout.addStretch()

        # Initialize OCR
        self._on_ocr_changed()

    def set_plugins(self, plugins: List[Plugin]):
        """Set the available plugins."""
        self.plugins = plugins
        self.plugin_combo.clear()
        self.plugin_combo.addItem("\u65e0 (\u9ed8\u8ba4)", None)

        for plugin in plugins:
            self.plugin_combo.addItem(f"{plugin.name} - {plugin.description}", plugin)

    def _on_ocr_changed(self):
        """Handle OCR engine change."""
        ocr_type = self.ocr_combo.currentData()

        try:
            if ocr_type == "paddle":
                self.current_ocr = PaddleOCREngine()
            elif ocr_type == "tesseract":
                self.current_ocr = TesseractOCREngine()
            elif ocr_type == "windows":
                self.current_ocr = WindowsOCREngine()

            if self.current_ocr and self.current_ocr.is_available:
                self.ocr_changed.emit(self.current_ocr)
            else:
                QMessageBox.warning(
                    self,
                    "OCR\u5f15\u64ce\u4e0d\u53ef\u7528",
                    f"{self.current_ocr.name if self.current_ocr else 'OCR'} \u4e0d\u53ef\u7528\u3002\n\u8bf7\u68c0\u67e5\u60a8\u7684\u5b89\u88c5\u3002"
                )

        except Exception as e:
            logger.error(f"Error initializing OCR engine: {e}")
            QMessageBox.critical(
                self,
                "OCR\u9519\u8bef",
                f"\u521d\u59cb\u5316OCR\u5f15\u64ce\u5931\u8d25:\n{str(e)}"
            )

    def _on_plugin_changed(self):
        """Handle plugin selection change."""
        self.current_plugin = self.plugin_combo.currentData()
        self.plugin_changed.emit(self.current_plugin)

    def _on_interval_changed(self):
        """Handle interval change."""
        seconds = self.interval_spin.value()
        self.interval_changed.emit(float(seconds))

    def _on_overlay_toggled(self, checked: bool):
        """Handle overlay toggle."""
        if checked:
            self.overlay_btn.setText("\u9690\u85cf\u76d1\u63a7\u6846\u67b6")
            self.show_overlay_requested.emit()
        else:
            self.overlay_btn.setText("\u663e\u793a\u76d1\u63a7\u6846\u67b6")
            self.hide_overlay_requested.emit()

    def _on_start_clicked(self):
        """Handle start button click."""
        logger.info("Start button clicked")
        self.start_monitoring_requested.emit()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("\u76d1\u63a7\u4e2d...")
        self.status_label.setStyleSheet("color: green;")

    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.stop_monitoring_requested.emit()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("\u76d1\u63a7\u5df2\u505c\u6b62")
        self.status_label.setStyleSheet("color: gray;")

    def _on_clear_clicked(self):
        """Handle clear history button click."""
        self.clear_history_requested.emit()

    def update_status(self, message: str, is_error: bool = False):
        """Update the status label."""
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet("color: red;")
        else:
            self.status_label.setStyleSheet("color: black;")

    def set_monitoring_state(self, is_running: bool):
        """Update UI based on monitoring state."""
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)

    def closeEvent(self, event):
        """Handle window close."""
        # Stop monitoring before closing
        self.stop_monitoring_requested.emit()
        event.accept()
