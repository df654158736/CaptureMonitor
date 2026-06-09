"""后台翻译线程:循环截图 → 管线 → 信号回主线程。UI 永不阻塞。"""

import time
import logging

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from utils.screen_capture import capture_region, physical_rect

logger = logging.getLogger(__name__)


class TranslationWorker(QThread):
    translation_ready = pyqtSignal(str, str)   # (原文, 译文)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, pipeline, get_region, get_scale, sample_interval_ms: int = 120):
        super().__init__()
        self.pipeline = pipeline
        self.get_region = get_region   # () -> (x, y, w, h) 逻辑坐标 或 None
        self.get_scale = get_scale     # () -> float devicePixelRatio
        self.sample_interval_ms = sample_interval_ms
        self._running = False
        self._force = False

    def request_force(self):
        """热键触发:下一帧强制翻译。"""
        self._force = True

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            region = self.get_region()
            if region and region[2] > 0 and region[3] > 0:
                try:
                    px = physical_rect(*region, self.get_scale())
                    image = capture_region(*px)
                    frame = np.asarray(image.convert("RGB"))
                    force, self._force = self._force, False
                    result = self.pipeline.process_frame(frame, time.monotonic(), force=force)
                    if result is not None:
                        self.translation_ready.emit(result.src_text, result.dst_text)
                except Exception as e:  # 单帧失败不能拖垮线程
                    logger.error(f"worker tick 失败: {e}")
                    self.error_occurred.emit(str(e))
            self.msleep(self.sample_interval_ms)
