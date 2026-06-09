"""译文回看面板:记录每次翻译(原文 + 译文),可导出。"""

import html as html_lib
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor

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
        self.text_edit.setStyleSheet(
            "QTextEdit { background:#fbfbfd; border:1px solid #d8dbe0;"
            " border-radius:6px; padding:6px; font-size:13px; }"
        )
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
        src_e = html_lib.escape(src).replace("\n", "<br>") or "(空)"
        dst_e = html_lib.escape(dst).replace("\n", "<br>") or "(空)"
        # 浅色卡片 + 左侧蓝色竖条 + 分隔线,清晰区分每条记录
        block = (
            f'<table width="100%" cellspacing="0" cellpadding="6" '
            f'style="margin-bottom:8px; background:#ffffff;">'
            f'<tr>'
            f'<td width="4" style="background:#3a7afe;"></td>'
            f'<td>'
            f'<span style="color:#3a7afe; font-weight:bold; font-size:11px;">⏱ {ts}</span>'
            f'<br><span style="color:#8a8f99;">{src_e}</span>'
            f'<br><span style="color:#1b1d22; font-size:15px; font-weight:bold;">{dst_e}</span>'
            f'</td></tr></table>'
            f'<div style="border-bottom:1px solid #e3e6ea; margin-bottom:8px;"></div>'
        )
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(block)

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
