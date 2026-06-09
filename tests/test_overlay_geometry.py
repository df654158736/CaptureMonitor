# tests/test_overlay_geometry.py
from ui.translation_overlay import dock_rect_below, within_snap


def test_dock_below_basic():
    # 采集框 (100,100,480,160),译文框高 120,间隙 6
    assert dock_rect_below(100, 100, 480, 160, overlay_h=120, gap=6) == (100, 266, 480, 120)


def test_dock_below_zero_gap():
    assert dock_rect_below(0, 0, 300, 50, overlay_h=80, gap=0) == (0, 50, 300, 80)


def test_within_snap_true_when_close():
    # 目标点距吸附点 10px,阈值 40 → 吸附
    assert within_snap(110, 270, 100, 266, threshold=40) is True


def test_within_snap_false_when_far():
    # 目标点距吸附点很远 → 不吸附
    assert within_snap(400, 600, 100, 266, threshold=40) is False


def test_within_snap_boundary_inclusive():
    # 恰好等于阈值仍吸附
    assert within_snap(140, 266, 100, 266, threshold=40) is True
    assert within_snap(141, 266, 100, 266, threshold=40) is False
