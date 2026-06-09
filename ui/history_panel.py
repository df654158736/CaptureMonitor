"""译文回看面板:记录每次翻译(原文 + 译文),可导出。"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class HistoryPanel(QWidget):
    clear_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("译文回看")
        self.setMinimumSize(420, 320)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("译文回看")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        btns = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        btns.addWidget(self.clear_btn)
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self._on_export)
        btns.addWidget(self.export_btn)
        layout.addLayout(btns)

        self.status_label = QLabel("0 条记录")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def add_translation(self, src: str, dst: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.text_edit.append(f"[{ts}] {src}\n    [译] {dst}\n")
        self._count += 1
        self.status_label.setText(f"{self._count} 条记录")
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

    def clear(self):
        self.text_edit.clear()
        self._count = 0
        self.status_label.setText("0 条记录")

    def _on_clear(self):
        self.clear()
        self.clear_requested.emit()

    def _on_export(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出译文", "translations.txt", "文本文件 (*.txt);;所有文件 (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.text_edit.toPlainText())
                self.status_label.setText(f"已导出到 {filepath}")
            except OSError as e:
                self.status_label.setText(f"导出失败: {e}")

    def closeEvent(self, event):
        self.hide()
        event.ignore()
