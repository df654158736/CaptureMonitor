# tests/test_change_detector.py
import numpy as np
from core.change_detector import (
    ChangeDetector, NO_CHANGE, CHANGING, STABLE_CHANGED,
)

BLACK = np.zeros((32, 32, 3), dtype=np.uint8)
WHITE = np.full((32, 32, 3), 255, dtype=np.uint8)


def test_first_frame_is_changing():
    d = ChangeDetector(stability_ms=400)
    assert d.feed(BLACK, now=0.0) == CHANGING


def test_not_stable_before_window_elapses():
    d = ChangeDetector(stability_ms=400)
    d.feed(BLACK, now=0.0)
    assert d.feed(BLACK, now=0.1) == NO_CHANGE   # 才过 100ms


def test_stable_change_after_window():
    d = ChangeDetector(stability_ms=400)
    d.feed(BLACK, now=0.0)
    assert d.feed(BLACK, now=0.5) == STABLE_CHANGED
    assert d.current_hash() is not None


def test_no_retrigger_for_same_content():
    d = ChangeDetector(stability_ms=400)
    d.feed(BLACK, now=0.0)
    d.feed(BLACK, now=0.5)                        # STABLE_CHANGED 已消费
    assert d.feed(BLACK, now=0.6) == NO_CHANGE    # 同内容不再触发


def test_new_content_triggers_again():
    d = ChangeDetector(stability_ms=400)
    d.feed(BLACK, now=0.0)
    d.feed(BLACK, now=0.5)
    assert d.feed(WHITE, now=0.7) == CHANGING     # 画面大变
    assert d.feed(WHITE, now=1.2) == STABLE_CHANGED


def test_hash_differs_for_different_frames():
    d1, d2 = ChangeDetector(), ChangeDetector()
    d1.feed(BLACK, now=0.0)
    d2.feed(WHITE, now=0.0)
    assert d1.current_hash() != d2.current_hash()
