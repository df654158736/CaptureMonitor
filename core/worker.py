"""后台翻译线程:循环截图 → 管线 → 信号回主线程。UI 永不阻塞。"""

import os
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

    def __init__(self, pipeline, get_region, get_scale, get_auto=None,
                 sample_interval_ms: int = 120, debug_dir: str = None):
        super().__init__()
        self.pipeline = pipeline
        self.get_region = get_region   # () -> (x, y, w, h) 逻辑坐标 或 None
        self.get_scale = get_scale     # () -> float devicePixelRatio
        self.get_auto = get_auto       # () -> bool;None 视为始终自动(兼容)
        self.sample_interval_ms = sample_interval_ms
        self.debug_dir = debug_dir     # 若设置,心跳时把截到的帧存成 debug_capture.png
        self._running = False
        self._force = False
        self._ticks = 0
        self._first = True
        self._heartbeat_every = max(1, int(2000 / max(sample_interval_ms, 1)))  # 约每 2 秒

    def request_force(self):
        """热键/点击触发:下一帧强制翻译。"""
        self._force = True

    def stop(self):
        self._running = False

    def _tick(self):
        """单次循环体。手动模式空闲(非自动且未被 force)时不截屏,返回 None。"""
        force, self._force = self._force, False
        auto = self.get_auto() if self.get_auto else True
        if not force and not auto:
            return None

        region = self.get_region()
        if not (region and region[2] > 0 and region[3] > 0):
            return None

        scale = self.get_scale()
        px = physical_rect(*region, scale)
        if self._first:
            logger.info("开始监控: 逻辑区域=%s 缩放=%s 物理像素=%s", region, scale, px)
            self._first = False
        image = capture_region(*px)
        frame = np.asarray(image.convert("RGB"))

        self._ticks += 1
        if self.debug_dir and self._ticks % self._heartbeat_every == 0:
            det = self.pipeline.detector
            logger.info("监控心跳: phys=%s 帧均值=%.1f hash=%s 上次MAD=%.1f",
                        px, float(frame.mean()), det.current_hash(),
                        getattr(det, "last_mad", 0.0))
            try:
                image.save(os.path.join(self.debug_dir, "debug_capture.png"))
            except Exception as e:
                logger.warning("保存 debug_capture.png 失败: %s", e)

        return self.pipeline.process_frame(
            frame, time.monotonic(), force=force,
            on_translating=lambda: self.status_changed.emit("翻译中…"),
        )

    def run(self):
        self._running = True
        while self._running:
            try:
                result = self._tick()
                if result is not None:
                    self.translation_ready.emit(result.src_text, result.dst_text)
                    self.status_changed.emit("译文已更新 " + time.strftime("%H:%M:%S"))
            except Exception as e:  # 单帧失败不能拖垮线程
                logger.error("worker tick 失败: %s", e)
                self.error_occurred.emit(str(e))
            self.msleep(self.sample_interval_ms)
