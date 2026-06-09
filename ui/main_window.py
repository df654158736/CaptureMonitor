"""主控制面板:密钥 / 语言 / 触发 / 采集框 / 译文框 / 开始停止。"""

import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    show_capture_requested = pyqtSignal()
    lock_toggled = pyqtSignal(bool)           # True=锁定开始, False=解锁停止
    show_overlay_requested = pyqtSignal(bool)
    view_history_requested = pyqtSignal()
    clear_history_requested = pyqtSignal()
    creds_changed = pyqtSignal(str, str)      # app_key, app_secret
    lang_changed = pyqtSignal(str, str)       # from, to

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self.setWindowTitle("实时翻译悬浮框")
        self.setMinimumSize(360, 380)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 有道密钥
        cred_group = QGroupBox("有道图片翻译密钥")
        cred_form = QFormLayout(cred_group)
        self.appkey_edit = QLineEdit(self._config["youdao"]["app_key"])
        self.secret_edit = QLineEdit(self._config["youdao"]["app_secret"])
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.appkey_edit.editingFinished.connect(self._on_creds)
        self.secret_edit.editingFinished.connect(self._on_creds)
        cred_form.addRow("应用ID:", self.appkey_edit)
        cred_form.addRow("密钥:", self.secret_edit)
        layout.addWidget(cred_group)

        # 语言方向
        lang_group = QGroupBox("语言方向")
        lang_layout = QHBoxLayout(lang_group)
        self.from_combo = QComboBox()
        self.from_combo.addItem("英文", "en")
        self.from_combo.addItem("日文", "jp")
        self.from_combo.addItem("自动", "auto")
        self.to_combo = QComboBox()
        self.to_combo.addItem("中文", "zh-CHS")
        self.from_combo.currentIndexChanged.connect(self._on_lang)
        self.to_combo.currentIndexChanged.connect(self._on_lang)
        lang_layout.addWidget(self.from_combo)
        lang_layout.addWidget(QLabel("→"))
        lang_layout.addWidget(self.to_combo)
        layout.addWidget(lang_group)

        # 控制
        ctrl_group = QGroupBox("控制")
        ctrl = QVBoxLayout(ctrl_group)
        self.capture_btn = QPushButton("显示采集框")
        self.capture_btn.setCheckable(True)
        self.capture_btn.toggled.connect(self._on_capture_toggle)
        ctrl.addWidget(self.capture_btn)

        self.start_btn = QPushButton("开始翻译")
        self.start_btn.setCheckable(True)
        self.start_btn.toggled.connect(self._on_start_toggle)
        ctrl.addWidget(self.start_btn)

        self.overlay_btn = QPushButton("显示译文框")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.setChecked(True)
        self.overlay_btn.toggled.connect(self.show_overlay_requested.emit)
        ctrl.addWidget(self.overlay_btn)

        self.history_btn = QPushButton("查看译文回看")
        self.history_btn.clicked.connect(self.view_history_requested.emit)
        ctrl.addWidget(self.history_btn)
        layout.addWidget(ctrl_group)

        hint = QLabel("热键 Alt+D:立即翻译当前画面")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)

        self.status_label = QLabel("就绪 — 请填密钥并拖动采集框到游戏文字上")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _on_creds(self):
        self.creds_changed.emit(self.appkey_edit.text().strip(), self.secret_edit.text().strip())

    def _on_lang(self):
        self.lang_changed.emit(self.from_combo.currentData(), self.to_combo.currentData())

    def _on_capture_toggle(self, checked):
        self.capture_btn.setText("隐藏采集框" if checked else "显示采集框")
        if checked:
            self.show_capture_requested.emit()

    def _on_start_toggle(self, checked):
        self.start_btn.setText("停止翻译" if checked else "开始翻译")
        self.lock_toggled.emit(checked)
        self.update_status("翻译中…" if checked else "已停止")

    def update_status(self, message: str, is_error: bool = False):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: red;" if is_error else "color: green;")

    def closeEvent(self, event):
        self.lock_toggled.emit(False)
        event.accept()
