# tests/test_screen_capture.py
from utils.screen_capture import physical_rect


def test_physical_rect_scale_1():
    assert physical_rect(10, 20, 100, 50, 1.0) == (10, 20, 100, 50)


def test_physical_rect_scale_1_5():
    assert physical_rect(10, 20, 100, 50, 1.5) == (15, 30, 150, 75)


def test_physical_rect_rounds():
    assert physical_rect(0, 0, 33, 33, 1.25) == (0, 0, 41, 41)  # 41.25 -> 41
