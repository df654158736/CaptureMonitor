"""实时翻译悬浮框 — 程序入口。"""

import os
import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.config import load_config, save_config
from core.backends import create_backend
from core.change_detector import ChangeDetector
from core.cache import LRUCache
from core.pipeline import TranslationPipeline
from core.worker import TranslationWorker
from core.hotkey import HotkeyManager
from ui.main_window import MainWindow
from ui.capture_box import CaptureBox
from ui.translation_overlay import TranslationOverlay
from ui.history_panel import HistoryPanel

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    config = load_config(CONFIG_PATH)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("RealtimeTranslate")

    # 后端 + 管线
    backend = create_backend(config)
    detector = ChangeDetector(
        change_threshold=config["detection"]["change_threshold"],
        stability_ms=config["detection"]["stability_ms"],
    )
    pipeline = TranslationPipeline(
        backend, detector=detector, cache=LRUCache(),
        src=config["lang"]["from"], dst=config["lang"]["to"],
    )

    # UI
    main_window = MainWindow(config)
    capture_box = CaptureBox(config)
    overlay = TranslationOverlay(config)
    history = HistoryPanel()

    # Worker
    worker = TranslationWorker(
        pipeline,
        get_region=lambda: (config["capture"]["x"], config["capture"]["y"],
                            config["capture"]["w"], config["capture"]["h"]),
        get_scale=capture_box.current_scale,
        sample_interval_ms=config["detection"]["sample_interval_ms"],
        debug_dir=os.path.dirname(os.path.abspath(__file__)),
    )

    # 热键
    hotkeys = HotkeyManager()
    hotkeys.register(config["trigger"]["hotkey"], worker.request_force)

    # ---- 接线 ----
    def refresh_backend(force_now=False):
        """按当前配置重建后端;切换引擎/改密钥后清缓存,可选立即翻译当前帧。"""
        pipeline.backend = create_backend(config)
        pipeline.cache = LRUCache()
        save_config(CONFIG_PATH, config)
        if force_now and worker.isRunning():
            worker.request_force()

    def creds_ok() -> bool:
        if config["backend"] == "volcano":
            v = config["volcano"]
            return bool(v["access_key"] and v["secret_key"])
        y = config["youdao"]
        return bool(y["app_key"] and y["app_secret"])

    def on_backend(name):
        config["backend"] = name
        main_window.update_status(f"已切换引擎: {'火山' if name == 'volcano' else '有道'}")
        refresh_backend(force_now=True)

    def on_youdao_creds(app_key, app_secret):
        config["youdao"]["app_key"] = app_key
        config["youdao"]["app_secret"] = app_secret
        refresh_backend()

    def on_volcano_creds(access_key, secret_key):
        config["volcano"]["access_key"] = access_key
        config["volcano"]["secret_key"] = secret_key
        refresh_backend()

    def on_lang(src, dst):
        config["lang"]["from"], config["lang"]["to"] = src, dst
        pipeline.src, pipeline.dst = src, dst
        save_config(CONFIG_PATH, config)

    def on_capture_geometry(x, y, w, h):
        overlay.dock_to(x, y, w, h)
        save_config(CONFIG_PATH, config)

    def on_lock(locked):
        if locked:
            if not creds_ok():
                engine = "火山" if config["backend"] == "volcano" else "有道"
                main_window.update_status(f"请先填写{engine}密钥", is_error=True)
                main_window.start_btn.setChecked(False)
                return
            capture_box.set_locked(True)
            if not worker.isRunning():
                worker.start()
        else:
            worker.stop()
            worker.wait(2000)
            capture_box.set_locked(False)

    def on_translation(src, dst):
        overlay.set_text(src, dst)
        history.add_translation(src, dst)

    main_window.backend_changed.connect(on_backend)
    main_window.youdao_creds_changed.connect(on_youdao_creds)
    main_window.volcano_creds_changed.connect(on_volcano_creds)
    main_window.lang_changed.connect(on_lang)
    main_window.show_capture_requested.connect(capture_box.show)
    main_window.hide_capture_requested.connect(capture_box.hide)
    main_window.lock_toggled.connect(on_lock)
    main_window.show_overlay_requested.connect(
        lambda show: overlay.setVisible(show)
    )
    main_window.view_history_requested.connect(history.show)
    main_window.clear_history_requested.connect(history.clear)

    capture_box.geometry_changed.connect(on_capture_geometry)
    worker.translation_ready.connect(on_translation)
    worker.status_changed.connect(lambda m: main_window.update_status(m))
    worker.error_occurred.connect(lambda m: main_window.update_status(f"错误: {m}", is_error=True))

    # 初始吸附 + 显示
    cap = config["capture"]
    if cap["w"] > 0:
        overlay.dock_to(cap["x"], cap["y"], cap["w"], cap["h"])
    main_window.show()
    overlay.show()

    def cleanup():
        worker.stop()
        worker.wait(2000)
        hotkeys.unregister()
        save_config(CONFIG_PATH, config)

    app.aboutToQuit.connect(cleanup)
    logger.info("实时翻译悬浮框已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
