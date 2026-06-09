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


def test_gradual_change_then_settle_triggers():
    """逐步累积的小幅变化(每帧间差异很小)停下来后,新稳定画面应触发翻译。

    复现日志中"画面停在新内容上却从不翻译"的场景:旧逻辑要求出现帧间大跳变来 arm,
    渐变不会 arm,于是永不触发。新逻辑只看"hash 稳定且与上次翻译不同"。
    """
    d = ChangeDetector(stability_ms=300)
    t = 0.0
    last_event = None
    # 每步均匀 +5(帧间差异很小),但每帧内容(dHash 均值字节)都在变
    for level in range(0, 60, 5):
        frame = np.full((32, 32, 3), level, dtype=np.uint8)
        last_event = d.feed(frame, now=t)
        t += 0.12
    assert last_event == CHANGING  # 渐变期间一直在变

    # 停在最终内容上,保持稳定超过 stability_ms → 应触发
    final = np.full((32, 32, 3), 55, dtype=np.uint8)
    d.feed(final, now=t)
    assert d.feed(final, now=t + 0.4) == STABLE_CHANGED
