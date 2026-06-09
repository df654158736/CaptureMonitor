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
    """基于 dHash 稳定性的变化检测 + 防抖。

    判定逻辑:
    - 每帧算 dHash。只要 hash 与上一帧不同 → 画面仍在变(CHANGING),刷新静止计时。
    - hash 连续 stability_ms 保持不变 → 画面已稳定;若该稳定内容与"上次已翻译"的不同
      → STABLE_CHANGED。
    - 关键:不再要求出现"帧间大跳变"来触发。即使是逐步累积的小幅变化(每两帧之间差异
      都很小,如终端逐行滚动),只要最终停下来形成一帧新的稳定画面,也会被翻译;而持续
      滚动期间(hash 一直在变)不会反复触发。

    `last_mad` 仅作诊断输出(帧间平均绝对差),不参与判定。
    """

    def __init__(self, change_threshold: float = 8.0, stability_ms: int = 400):
        self.change_threshold = change_threshold  # 保留以兼容配置;现仅用于诊断
        self.stability_ms = stability_ms
        self._prev_small = None
        self._cur_hash = None
        self._hash_changed_at = None
        self._last_translated_hash = None
        self.last_mad = 0.0  # 最近一次帧间平均绝对差(诊断用)

    def feed(self, frame: np.ndarray, now: float) -> str:
        h = _dhash(frame)

        # 诊断用:帧间平均绝对差(不参与判定)
        small = _to_small_gray(frame)
        if self._prev_small is not None:
            self.last_mad = float(np.mean(np.abs(small - self._prev_small)))
        self._prev_small = small

        if h != self._cur_hash:
            self._cur_hash = h
            self._hash_changed_at = now
            return CHANGING

        # hash 与上一帧相同 → 画面静止
        if self._hash_changed_at is None:
            self._hash_changed_at = now
        if (now - self._hash_changed_at) * 1000.0 >= self.stability_ms:
            if h != self._last_translated_hash:
                self._last_translated_hash = h
                return STABLE_CHANGED

        return NO_CHANGE

    def current_hash(self):
        return self._cur_hash

    def notify_translated(self, hash_value: str) -> None:
        """缓存命中或强制翻译后,标记该帧已翻译,避免重复触发。"""
        self._last_translated_hash = hash_value
