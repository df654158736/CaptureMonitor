"""图像变化检测 + 防抖(基于 dHash 汉明距离容差)。

调用方每帧传入 (frame: HxWx3 uint8 numpy 数组, now: 单调秒)。
返回事件:NO_CHANGE / CHANGING / STABLE_CHANGED。

判定:相邻两帧 dHash 汉明距离 ≤ stable_hamming 视为"没动";连续没动达 stability_ms
后,若稳定内容与"上次已翻译"汉明距离 ≥ change_hamming(或从未翻译过)→ STABLE_CHANGED。
容忍动画/光标的轻微抖动,使画面"停得下来",修复"该翻译时不翻译"的漏触发。
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
    # 前置均值字节:纯色图的 dHash 全 0,靠它区分亮度(全黑 vs 全白)。
    mean_byte = int(arr.mean()) & 0xFF
    return f"{mean_byte:02x}{format(bits, '016x')}"


def _bits_of(hash_str: str) -> int:
    """整串(均值字节 + 64 位 dHash = 72 位)转 int,供汉明比较。"""
    return int(hash_str, 16)


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


class ChangeDetector:
    def __init__(self, change_threshold: float = 8.0, stability_ms: int = 400,
                 stable_hamming: int = 3, change_hamming: int = 5):
        self.change_threshold = change_threshold  # 保留以兼容配置;现仅诊断
        self.stability_ms = stability_ms
        self.stable_hamming = stable_hamming
        self.change_hamming = change_hamming
        self._prev_small = None
        self._cur_hash = None
        self._anchor_bits = None
        self._anchor_at = None
        self._last_translated_bits = None
        self.last_mad = 0.0  # 帧间平均绝对差(诊断用)

    def feed(self, frame: np.ndarray, now: float) -> str:
        h = _dhash(frame)
        bits = _bits_of(h)
        self._cur_hash = h  # 始终是最新帧,force 翻译时缓存键正确

        small = _to_small_gray(frame)
        if self._prev_small is not None:
            self.last_mad = float(np.mean(np.abs(small - self._prev_small)))
        self._prev_small = small

        if self._anchor_bits is None:
            self._anchor_bits = bits
            self._anchor_at = now
            return CHANGING

        if _hamming(bits, self._anchor_bits) > self.stable_hamming:
            # 超出容差 → 画面在动:换锚点、刷新静止计时
            self._anchor_bits = bits
            self._anchor_at = now
            return CHANGING

        # 容差内 → 画面停住
        if (now - self._anchor_at) * 1000.0 >= self.stability_ms:
            if (self._last_translated_bits is None
                    or _hamming(self._anchor_bits, self._last_translated_bits) >= self.change_hamming):
                self._last_translated_bits = self._anchor_bits  # 自标记,避免同窗口反复触发
                return STABLE_CHANGED
        return NO_CHANGE

    def current_hash(self):
        return self._cur_hash

    def notify_translated(self, hash_value: str) -> None:
        """force/缓存命中路径标记已翻译,避免自动模式随后重复触发同一内容。"""
        self._last_translated_bits = _bits_of(hash_value)
