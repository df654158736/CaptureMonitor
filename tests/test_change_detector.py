# tests/test_change_detector.py
import numpy as np
import core.change_detector as cd
from core.change_detector import (
    ChangeDetector, NO_CHANGE, CHANGING, STABLE_CHANGED,
)

BLACK = np.zeros((32, 32, 3), dtype=np.uint8)
WHITE = np.full((32, 32, 3), 255, dtype=np.uint8)
DUMMY = np.zeros((8, 8, 3), dtype=np.uint8)


def _hx(mean, bits):
    return f"{mean:02x}{bits:016x}"


def _fake_hashes(monkeypatch, hashes):
    it = iter(hashes)
    monkeypatch.setattr(cd, "_dhash", lambda frame: next(it))


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


def test_jitter_within_tolerance_does_not_reset_timer(monkeypatch):
    # 抖动帧与锚点差 2 位(≤ stable_hamming=3),不应重置静止计时
    base, jit = 0x0, 0x3
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, jit), _hx(0, base)])
    d = ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    assert d.feed(DUMMY, 0.0) == CHANGING        # 首帧
    assert d.feed(DUMMY, 0.2) == NO_CHANGE        # 抖动,200ms<300
    assert d.feed(DUMMY, 0.4) == STABLE_CHANGED    # 计时未被抖动重置 → 400ms≥300 触发


def test_jitter_after_translate_no_retrigger(monkeypatch):
    base, jit = 0x0, 0x3
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, base), _hx(0, jit), _hx(0, base)])
    d = ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    d.feed(DUMMY, 0.0)
    assert d.feed(DUMMY, 0.4) == STABLE_CHANGED    # 自标记 last=base
    assert d.feed(DUMMY, 0.5) == NO_CHANGE          # 抖动与 last 差 <change_hamming
    assert d.feed(DUMMY, 0.6) == NO_CHANGE


def test_change_beyond_threshold_triggers_again(monkeypatch):
    base, new = 0x0, 0x1F   # popcount(0x1F)=5
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, base), _hx(0, new), _hx(0, new)])
    d = ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    d.feed(DUMMY, 0.0)
    assert d.feed(DUMMY, 0.4) == STABLE_CHANGED    # last=base
    assert d.feed(DUMMY, 0.5) == CHANGING           # new 与 base 差 5 >3
    assert d.feed(DUMMY, 0.9) == STABLE_CHANGED     # 差 5 ≥ change_hamming → 再次触发


def test_scrolling_then_settle(monkeypatch):
    # 连续大幅变化期间从不触发;停下后触发一次
    seq = [0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x55, 0x55]
    _fake_hashes(monkeypatch, [_hx(0, b) for b in seq])
    d = ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    t = 0.0
    events = []
    for _ in range(5):
        events.append(d.feed(DUMMY, t)); t += 0.1
    assert all(e == CHANGING for e in events)       # 滚动期间一直在变
    assert d.feed(DUMMY, t) == NO_CHANGE             # 刚停,未满 stability
    assert d.feed(DUMMY, t + 0.4) == STABLE_CHANGED   # 停稳 → 触发
