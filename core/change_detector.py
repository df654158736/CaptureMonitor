"""图像变化检测 + 防抖。

调用方每帧传入 (frame: HxWx3 uint8 numpy 数组, now: 单调秒)。
返回事件:NO_CHANGE / CHANGING / STABLE_CHANGED。
STABLE_CHANGED = 画面变化后已稳定 stability_ms,且与上次翻译过的帧不同。
"""

import numpy as np
from PIL import Image

NO_CHANGE = "NO_CHANGE"
CHANGING = "CHANGING"
STABLE_CHANGED = "STABLE_CHANGED"


def _to_small_gray(frame: np.ndarray, size: int = 32) -> np.ndarray:
    img = Image.fromarray(frame).convert("L").resize((size, size))
    return np.asarray(img, dtype=np.float32)


def _dhash(frame: np.ndarray, hash_size: int = 8) -> str:
    img = Image.fromarray(frame).convert("L").resize((hash_size + 1, hash_size))
    arr = np.asarray(img, dtype=np.int16)
    diff = arr[:, 1:] > arr[:, :-1]
    bits = 0
    for bit in diff.flatten():
        bits = (bits << 1) | int(bit)
    # Prepend mean intensity byte so uniform images of different brightness
    # (e.g. solid black vs solid white) produce distinct hashes; dHash alone
    # yields all-zero bits for any uniform-color image.
    mean_byte = int(arr.mean()) & 0xFF
    return f"{mean_byte:02x}{format(bits, '016x')}"


class ChangeDetector:
    def __init__(self, change_threshold: float = 8.0, stability_ms: int = 400):
        self.change_threshold = change_threshold
        self.stability_ms = stability_ms
        self._prev_small = None
        self._cur_hash = None
        self._last_change_at = None
        self._pending = False
        self._last_translated_hash = None
        self.last_mad = 0.0  # 最近一次帧间平均绝对差(诊断用)

    def feed(self, frame: np.ndarray, now: float) -> str:
        small = _to_small_gray(frame)
        self._cur_hash = _dhash(frame)

        if self._prev_small is None:
            self._prev_small = small
            self._last_change_at = now
            self._pending = True
            return CHANGING

        mad = float(np.mean(np.abs(small - self._prev_small)))
        self.last_mad = mad
        self._prev_small = small

        if mad > self.change_threshold:
            self._last_change_at = now
            self._pending = True
            return CHANGING

        if self._pending and (now - self._last_change_at) * 1000.0 >= self.stability_ms:
            self._pending = False
            if self._cur_hash != self._last_translated_hash:
                self._last_translated_hash = self._cur_hash
                return STABLE_CHANGED

        return NO_CHANGE

    def current_hash(self):
        return self._cur_hash

    def notify_translated(self, hash_value: str) -> None:
        """缓存命中或强制翻译后,标记该帧已翻译,避免重复触发。"""
        self._last_translated_hash = hash_value
        self._pending = False
