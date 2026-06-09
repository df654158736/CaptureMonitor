# tests/test_overlay_geometry.py
from ui.translation_overlay import dock_rect_below


def test_dock_below_basic():
    # 采集框 (100,100,480,160),译文框高 120,间隙 6
    assert dock_rect_below(100, 100, 480, 160, overlay_h=120, gap=6) == (100, 266, 480, 120)


def test_dock_below_zero_gap():
    assert dock_rect_below(0, 0, 300, 50, overlay_h=80, gap=0) == (0, 50, 300, 80)
