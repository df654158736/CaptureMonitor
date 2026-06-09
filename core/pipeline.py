"""纯编排:变化检测 → 缓存 → 后端。无 Qt、无线程,可完整单测。"""

import io
import logging
import time
from typing import Optional

import numpy as np
from PIL import Image

from core.cache import LRUCache
from core.change_detector import ChangeDetector, STABLE_CHANGED
from core.backends.base import TranslationBackend, TranslationResult

logger = logging.getLogger(__name__)


def _frame_to_png(frame: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(frame).save(buf, format="PNG")
    return buf.getvalue()


class TranslationPipeline:
    def __init__(self, backend: TranslationBackend, detector: ChangeDetector = None,
                 cache: LRUCache = None, src: str = "en", dst: str = "zh-CHS", to_png=None):
        self.backend = backend
        self.detector = detector or ChangeDetector()
        self.cache = cache or LRUCache()
        self.src = src
        self.dst = dst
        self._to_png = to_png or _frame_to_png

    def process_frame(self, frame: np.ndarray, now: float,
                      force: bool = False, on_translating=None) -> Optional[TranslationResult]:
        event = self.detector.feed(frame, now)
        if not force and event != STABLE_CHANGED:
            return None

        h = self.detector.current_hash()
        cached = self.cache.get(h)
        if cached is not None:
            logger.info("缓存命中 (hash=%s),返回已有译文", h)
            self.detector.notify_translated(h)
            return cached

        logger.info("检测到稳定变化%s,调用有道翻译… hash=%s",
                    "(热键强制)" if force else "", h)
        if on_translating:
            on_translating()
        t0 = time.monotonic()
        result = self.backend.translate_image(self._to_png(frame), self.src, self.dst)
        logger.info("翻译完成 (%.0fms): %r", (time.monotonic() - t0) * 1000, result.dst_text[:60])
        self.cache.put(h, result)
        self.detector.notify_translated(h)
        return result
