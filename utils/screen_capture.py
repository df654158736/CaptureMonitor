"""屏幕区域截图(mss)+ 逻辑坐标→物理像素换算。

mss 实例非线程安全:用 threading.local 保证每线程一个实例。
"""

import threading

import mss
from PIL import Image

_local = threading.local()


def physical_rect(x, y, w, h, scale):
    """Qt 逻辑坐标矩形 → 物理像素矩形(四舍五入)。"""
    return (round(x * scale), round(y * scale), round(w * scale), round(h * scale))


def _get_sct():
    if getattr(_local, "sct", None) is None:
        _local.sct = mss.mss()
    return _local.sct


def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """按物理像素坐标截取一块区域,返回 RGB PIL.Image。"""
    if w <= 0 or h <= 0:
        return Image.new("RGB", (1, 1), "white")
    monitor = {"left": int(x), "top": int(y), "width": int(w), "height": int(h)}
    shot = _get_sct().grab(monitor)
    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
