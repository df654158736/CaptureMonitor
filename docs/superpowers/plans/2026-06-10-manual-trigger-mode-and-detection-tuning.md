# 手动点击翻译模式 + 自动检测优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给实时翻译悬浮框增加「手动点击译文框翻译」模式(默认),并把自动检测从精确哈希相等改为汉明距离容差以修复漏触发。

**Architecture:** 新增互斥的翻译模式开关(手动/自动)。手动模式下后台线程空闲不截屏,仅在轻点译文框或按 Alt+D 时截当前画面翻译一次。自动模式改用「锚点 + 汉明容差」判定稳定与变化,容忍动画抖动。译文框手势重构:轻点=翻译、拖动=移动、右下角小按钮=归位(取消双击)。

**Tech Stack:** Python 3、PyQt6、numpy、Pillow、pytest(offscreen Qt)。

参考设计稿:`docs/superpowers/specs/2026-06-10-manual-trigger-mode-and-detection-tuning-design.md`

约束:`config.json` 含密钥、已 gitignore,任何任务都不得提交它。

---

### Task 1: 配置 — 默认手动模式 + 归一化 + 新检测参数

**Files:**
- Modify: `core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_config.py` 末尾追加:

```python
def test_default_mode_is_manual():
    assert DEFAULT_CONFIG["trigger"]["mode"] == "manual"
    assert DEFAULT_CONFIG["detection"]["stable_hamming"] == 3
    assert DEFAULT_CONFIG["detection"]["change_hamming"] == 5


def test_legacy_auto_hotkey_normalized(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"trigger": {"mode": "auto+hotkey"}}), encoding="utf-8")
    assert load_config(str(path))["trigger"]["mode"] == "auto"


def test_unknown_mode_falls_back_to_manual(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"trigger": {"mode": "whatever"}}), encoding="utf-8")
    assert load_config(str(path))["trigger"]["mode"] == "manual"


def test_valid_modes_preserved(tmp_path):
    for m in ("manual", "auto"):
        path = tmp_path / f"{m}.json"
        path.write_text(json.dumps({"trigger": {"mode": m}}), encoding="utf-8")
        assert load_config(str(path))["trigger"]["mode"] == m
```

- [ ] **Step 2: 运行,确认失败**

Run: `pytest tests/test_config.py -v`
Expected: 新增 4 个测试 FAIL(`stable_hamming` KeyError / mode 仍是 `auto+hotkey` 等)。

- [ ] **Step 3: 改 `core/config.py`**

把 `DEFAULT_CONFIG` 的这两行改为:

```python
    "trigger": {"mode": "manual", "hotkey": "alt+d"},  # mode: manual | auto
    "detection": {
        "sample_interval_ms": 120,
        "stability_ms": 400,
        "change_threshold": 8,   # 保留,仅诊断
        "stable_hamming": 3,     # 相邻两帧 dHash 汉明距离 ≤ 此值视为"没动"
        "change_hamming": 5,     # 稳定内容与上次已翻译汉明距离 ≥ 此值才算"换了"
    },
```

把 `load_config` 的 `return _deep_merge(...)` 那一行替换为:

```python
    merged = _deep_merge(DEFAULT_CONFIG, data)
    mode = merged.get("trigger", {}).get("mode")
    if mode not in ("manual", "auto"):
        merged["trigger"]["mode"] = "auto" if (isinstance(mode, str) and "auto" in mode) else "manual"
    return merged
```

- [ ] **Step 4: 运行,确认通过**

Run: `pytest tests/test_config.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add core/config.py tests/test_config.py
git commit -m "feat(config): 默认手动模式 + 旧 mode 归一化 + 汉明容差参数"
```

---

### Task 2: 变化检测 — 汉明距离容差

**Files:**
- Modify: `core/change_detector.py`
- Test: `tests/test_change_detector.py`

- [ ] **Step 1: 写新的失败测试**

先**删除** `tests/test_change_detector.py` 中的 `test_gradual_change_then_settle_triggers`(其构造的"均匀亮度渐变"在新的容差语义下属于"亚阈值漂移",由下面更精确的 `test_scrolling_then_settle` 取代)。保留其余 6 个用例不动。

在文件顶部 import 之后追加一个用 fake `_dhash` 精确控制汉明距离的工具与新用例:

```python
import core.change_detector as cd

DUMMY = np.zeros((8, 8, 3), dtype=np.uint8)


def _hx(mean, bits):
    return f"{mean:02x}{bits:016x}"


def _fake_hashes(monkeypatch, hashes):
    it = iter(hashes)
    monkeypatch.setattr(cd, "_dhash", lambda frame: next(it))


def test_jitter_within_tolerance_does_not_reset_timer(monkeypatch):
    # 抖动帧与锚点差 2 位(≤ stable_hamming=3),不应重置静止计时
    base, jit = 0x0, 0x3
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, jit), _hx(0, base)])
    d = cd.ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    assert d.feed(DUMMY, 0.0) == cd.CHANGING       # 首帧
    assert d.feed(DUMMY, 0.2) == cd.NO_CHANGE       # 抖动,200ms<300
    assert d.feed(DUMMY, 0.4) == cd.STABLE_CHANGED   # 计时未被抖动重置 → 400ms≥300 触发


def test_jitter_after_translate_no_retrigger(monkeypatch):
    base, jit = 0x0, 0x3
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, base), _hx(0, jit), _hx(0, base)])
    d = cd.ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    d.feed(DUMMY, 0.0)
    assert d.feed(DUMMY, 0.4) == cd.STABLE_CHANGED   # 自标记 last=base
    assert d.feed(DUMMY, 0.5) == cd.NO_CHANGE         # 抖动与 last 差 <change_hamming
    assert d.feed(DUMMY, 0.6) == cd.NO_CHANGE


def test_change_beyond_threshold_triggers_again(monkeypatch):
    base, new = 0x0, 0x1F   # popcount(0x1F)=5
    _fake_hashes(monkeypatch, [_hx(0, base), _hx(0, base), _hx(0, new), _hx(0, new)])
    d = cd.ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    d.feed(DUMMY, 0.0)
    assert d.feed(DUMMY, 0.4) == cd.STABLE_CHANGED   # last=base
    assert d.feed(DUMMY, 0.5) == cd.CHANGING          # new 与 base 差 5 >3
    assert d.feed(DUMMY, 0.9) == cd.STABLE_CHANGED    # 差 5 ≥ change_hamming → 再次触发


def test_scrolling_then_settle(monkeypatch):
    # 连续大幅变化期间从不触发;停下后触发一次
    seq = [0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x55, 0x55]
    _fake_hashes(monkeypatch, [_hx(0, b) for b in seq])
    d = cd.ChangeDetector(stability_ms=300, stable_hamming=3, change_hamming=5)
    t = 0.0
    events = []
    for _ in range(5):
        events.append(d.feed(DUMMY, t)); t += 0.1
    assert all(e == cd.CHANGING for e in events)      # 滚动期间一直在变
    assert d.feed(DUMMY, t) == cd.NO_CHANGE            # 刚停,未满 stability
    assert d.feed(DUMMY, t + 0.4) == cd.STABLE_CHANGED  # 停稳 → 触发
```

- [ ] **Step 2: 运行,确认失败**

Run: `pytest tests/test_change_detector.py -v`
Expected: 4 个新用例 FAIL(旧实现无 `stable_hamming`/`change_hamming` 参数,或行为不符),原 6 个仍 PASS。

- [ ] **Step 3: 重写 `core/change_detector.py`**

把整个文件替换为(保留 `_dhash`/`_to_small_gray` 不变,新增 `_bits_of`/`_hamming`,重写类):

```python
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
```

- [ ] **Step 4: 运行,确认全绿**

Run: `pytest tests/test_change_detector.py -v`
Expected: 全部 PASS(原 6 个 + 新 4 个)。

- [ ] **Step 5: 提交**

```bash
git add core/change_detector.py tests/test_change_detector.py
git commit -m "feat(detector): dHash 汉明距离容差判定,修复动画背景漏触发"
```

---

### Task 3: 后台线程 — 手动模式空闲不截屏

**Files:**
- Modify: `core/worker.py`
- Test: `tests/test_worker_tick.py`(新建)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_worker_tick.py`:

```python
"""worker 单次循环体 _tick 的门控测试(不启动线程)。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image

from core.backends.base import TranslationResult
from core.worker import TranslationWorker


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class DummyPipeline:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def process_frame(self, frame, now, force=False, on_translating=None):
        self.calls.append(force)
        return self.result


def test_tick_manual_idle_does_not_capture(app):
    def boom():
        raise AssertionError("手动空闲不应截屏(get_region 不该被调用)")

    w = TranslationWorker(DummyPipeline(), get_region=boom,
                          get_scale=lambda: 1.0, get_auto=lambda: False, debug_dir=None)
    assert w._tick() is None  # 无 force + 非自动 → 直接返回,boom 未触发


def test_tick_force_translates_then_idles(app, monkeypatch):
    monkeypatch.setattr("core.worker.capture_region", lambda *a: Image.new("RGB", (4, 4)))
    res = TranslationResult("Hi", "你好", [])
    pipe = DummyPipeline(res)
    w = TranslationWorker(pipe, get_region=lambda: (0, 0, 10, 10),
                          get_scale=lambda: 1.0, get_auto=lambda: False, debug_dir=None)
    w.request_force()
    assert w._tick() is res          # force 截一帧翻译
    assert pipe.calls == [True]      # force 透传给管线
    assert w._tick() is None         # force 已消费,回到空闲不截屏


def test_tick_auto_captures_each_frame(app, monkeypatch):
    monkeypatch.setattr("core.worker.capture_region", lambda *a: Image.new("RGB", (4, 4)))
    pipe = DummyPipeline(None)       # 管线判定无变化
    w = TranslationWorker(pipe, get_region=lambda: (0, 0, 10, 10),
                          get_scale=lambda: 1.0, get_auto=lambda: True, debug_dir=None)
    assert w._tick() is None
    assert pipe.calls == [False]     # 自动模式:截帧并交管线,force=False
```

- [ ] **Step 2: 运行,确认失败**

Run: `pytest tests/test_worker_tick.py -v`
Expected: FAIL(`TranslationWorker` 还没有 `get_auto` 参数,也没有 `_tick`)。

- [ ] **Step 3: 改 `core/worker.py`**

整体替换为(新增 `get_auto`、抽出 `_tick`,`run` 改为循环调用):

```python
"""后台翻译线程:循环截图 → 管线 → 信号回主线程。UI 永不阻塞。"""

import os
import time
import logging

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from utils.screen_capture import capture_region, physical_rect

logger = logging.getLogger(__name__)


class TranslationWorker(QThread):
    translation_ready = pyqtSignal(str, str)   # (原文, 译文)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, pipeline, get_region, get_scale, get_auto=None,
                 sample_interval_ms: int = 120, debug_dir: str = None):
        super().__init__()
        self.pipeline = pipeline
        self.get_region = get_region   # () -> (x, y, w, h) 逻辑坐标 或 None
        self.get_scale = get_scale     # () -> float devicePixelRatio
        self.get_auto = get_auto       # () -> bool;None 视为始终自动(兼容)
        self.sample_interval_ms = sample_interval_ms
        self.debug_dir = debug_dir
        self._running = False
        self._force = False
        self._ticks = 0
        self._first = True
        self._heartbeat_every = max(1, int(2000 / max(sample_interval_ms, 1)))

    def request_force(self):
        """热键/点击触发:下一帧强制翻译。"""
        self._force = True

    def stop(self):
        self._running = False

    def _tick(self):
        """单次循环体。手动模式空闲(非自动且未被 force)时不截屏,返回 None。"""
        force, self._force = self._force, False
        auto = self.get_auto() if self.get_auto else True
        if not force and not auto:
            return None

        region = self.get_region()
        if not (region and region[2] > 0 and region[3] > 0):
            return None

        scale = self.get_scale()
        px = physical_rect(*region, scale)
        if self._first:
            logger.info("开始监控: 逻辑区域=%s 缩放=%s 物理像素=%s", region, scale, px)
            self._first = False
        image = capture_region(*px)
        frame = np.asarray(image.convert("RGB"))

        self._ticks += 1
        if self.debug_dir and self._ticks % self._heartbeat_every == 0:
            det = self.pipeline.detector
            logger.info("监控心跳: phys=%s 帧均值=%.1f hash=%s 上次MAD=%.1f",
                        px, float(frame.mean()), det.current_hash(),
                        getattr(det, "last_mad", 0.0))
            try:
                image.save(os.path.join(self.debug_dir, "debug_capture.png"))
            except Exception as e:
                logger.warning("保存 debug_capture.png 失败: %s", e)

        return self.pipeline.process_frame(
            frame, time.monotonic(), force=force,
            on_translating=lambda: self.status_changed.emit("翻译中…"),
        )

    def run(self):
        self._running = True
        while self._running:
            try:
                result = self._tick()
                if result is not None:
                    self.translation_ready.emit(result.src_text, result.dst_text)
                    self.status_changed.emit("译文已更新 " + time.strftime("%H:%M:%S"))
            except Exception as e:  # 单帧失败不能拖垮线程
                logger.error("worker tick 失败: %s", e)
                self.error_occurred.emit(str(e))
            self.msleep(self.sample_interval_ms)
```

- [ ] **Step 4: 运行,确认通过**

Run: `pytest tests/test_worker_tick.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add core/worker.py tests/test_worker_tick.py
git commit -m "feat(worker): 手动模式空闲不截屏,抽出可测的 _tick 门控"
```

---

### Task 4: 译文框 — 轻点翻译 + 手势重构 + 归位按钮

**Files:**
- Modify: `ui/translation_overlay.py`
- Test: `tests/test_translation_overlay.py`(新建)

- [ ] **Step 1: 写失败测试**

新建 `tests/test_translation_overlay.py`:

```python
"""译文框交互测试(Qt offscreen)。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy

import pytest
from PyQt6.QtCore import QPointF, QEvent, Qt
from PyQt6.QtGui import QMouseEvent

from core.config import DEFAULT_CONFIG


@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _overlay(mode="manual"):
    from ui.translation_overlay import TranslationOverlay
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["trigger"]["mode"] = mode
    return cfg, TranslationOverlay(cfg)


def _press(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mousePressEvent(e)


def _move(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseMove, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mouseMoveEvent(e)


def _release(w, x, y):
    e = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(x, y), QPointF(x, y),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier)
    w.mouseReleaseEvent(e)


def test_tap_emits_translate_requested(app):
    _cfg, ov = _overlay()
    ov.setGeometry(500, 500, 480, 160)
    got = []
    ov.translate_requested.connect(lambda: got.append(1))
    _press(ov, 520, 520)
    _release(ov, 520, 520)        # 原地松开 = 轻点
    assert got == [1]


def test_drag_does_not_emit_translate(app):
    _cfg, ov = _overlay()
    ov.setGeometry(500, 500, 480, 160)
    got = []
    ov.translate_requested.connect(lambda: got.append(1))
    _press(ov, 520, 520)
    _move(ov, 600, 600)           # 移动 >4px
    _release(ov, 600, 600)
    assert got == []              # 拖动不算翻译


def test_redock_button_visibility_and_action(app):
    cfg, ov = _overlay()
    ov.dock_to(100, 100, 480, 160)     # 吸附 → 按钮隐藏
    assert ov.redock_btn.isHidden()
    cfg["overlay"]["detached"] = True  # 模拟脱离
    ov.redock_btn.show()
    assert not ov.redock_btn.isHidden()
    ov.redock_btn.click()              # 归位
    assert cfg["overlay"]["detached"] is False
    assert ov.redock_btn.isHidden()


def test_set_mode_updates_placeholder(app):
    _cfg, ov = _overlay(mode="manual")
    assert ov.dst_label.text() == "点此翻译"
    ov.set_mode("auto")
    assert ov.dst_label.text() == "等待翻译…"
    ov.set_text("Hi", "你好")
    ov.set_mode("manual")              # 已有译文,占位不再覆盖
    assert ov.dst_label.text() == "你好"
```

- [ ] **Step 2: 运行,确认失败**

Run: `pytest tests/test_translation_overlay.py -v`
Expected: FAIL(无 `translate_requested` 信号 / `redock_btn` / `set_mode`)。

- [ ] **Step 3: 改 `ui/translation_overlay.py`**

① import 增加 `QPushButton`:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizeGrip, QPushButton
```

② 在文件常量区(`SNAP_DISTANCE` 旁)增加:

```python
TAP_MOVE_TOLERANCE = 4  # 按下到松开位移 ≤ 此值(逻辑像素)视为轻点而非拖动
```

③ 类信号区增加:

```python
    translate_requested = pyqtSignal()  # 轻点译文框 → 请求翻译当前画面
```

④ `__init__` 里,在 `self._show_source = ...` 之后增加状态:

```python
        self._mode = config["trigger"].get("mode", "manual")
        self._has_text = False
        self._press_global = None
        self._moved = False
```

⑤ `__init__` 创建 `self.dst_label` 之后,把其初始文案改为按模式占位(删掉原来硬编码的 `"等待翻译…"` 初值即可,改为):

```python
        self.dst_label = QLabel(self._placeholder())
```

⑥ 在 `grip` 之后(`__init__` 末尾 `setWindowOpacity` 之前)增加归位按钮:

```python
        self.redock_btn = QPushButton("📌", self)
        self.redock_btn.setFixedSize(24, 24)
        self.redock_btn.setToolTip("归位到采集框下方")
        self.redock_btn.setStyleSheet(
            "QPushButton{background:rgba(58,122,254,210); color:white;"
            " border:none; border-radius:12px; font-size:12px;}"
            "QPushButton:hover{background:rgba(58,122,254,255);}"
        )
        self.redock_btn.clicked.connect(self.redock)
        self.redock_btn.hide()
```

⑦ 新增方法(放在 `set_text` 附近):

```python
    def _placeholder(self) -> str:
        return "点此翻译" if self._mode == "manual" else "等待翻译…"

    def set_mode(self, mode: str):
        self._mode = mode
        if not self._has_text:
            self.dst_label.setText(self._placeholder())

    def resizeEvent(self, event):
        self.redock_btn.move(self.width() - self.redock_btn.width() - 8, 8)
        super().resizeEvent(event)
```

⑧ `set_text` 改为标记已有译文:

```python
    def set_text(self, src: str, dst: str):
        self._has_text = True
        if self._show_source:
            self.src_label.setText(src)
        self.dst_label.setText(dst or "(无文字)")
```

⑨ `dock_to` 末尾(成功吸附后)隐藏按钮 —— 把方法改为:

```python
    def dock_to(self, cap_x, cap_y, cap_w, cap_h):
        """被采集框调用:记住采集框位置;未脱离时吸附到其下方并跟随。"""
        self._cap_rect = (cap_x, cap_y, cap_w, cap_h)
        if self._config["overlay"].get("detached"):
            return
        x, y, w, h = dock_rect_below(cap_x, cap_y, cap_w, cap_h, self.height())
        self.setGeometry(x, y, w, h)
        self.redock_btn.hide()
```

⑩ **删除** `mouseDoubleClickEvent`(取消双击归位)。

⑪ 重写鼠标三件套(轻点/拖动判定 + 脱离时显示按钮):

```python
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global = event.globalPosition().toPoint()
            self._moved = False

    def mouseMoveEvent(self, event):
        if self._drag_offset is None:
            return
        cur = event.globalPosition().toPoint()
        if not self._moved and self._press_global is not None:
            d = cur - self._press_global
            if abs(d.x()) > TAP_MOVE_TOLERANCE or abs(d.y()) > TAP_MOVE_TOLERANCE:
                self._moved = True
        if not self._moved:
            return
        target = cur - self._drag_offset

        # 拖到采集框下方吸附点附近 → 自动吸附并重新附着
        if self._cap_rect:
            dx, dy, dw, dh = dock_rect_below(*self._cap_rect, self.height())
            if within_snap(target.x(), target.y(), dx, dy):
                if self._config["overlay"].get("detached"):
                    self._config["overlay"]["detached"] = False
                self.setGeometry(dx, dy, dw, dh)
                self.redock_btn.hide()
                return

        # 否则视为脱离,自由移动
        if not self._config["overlay"].get("detached"):
            self._config["overlay"]["detached"] = True
            self.detached.emit()
        self.redock_btn.show()
        self.move(target)

    def mouseReleaseEvent(self, event):
        was_tap = self._drag_offset is not None and not self._moved
        self._drag_offset = None
        self._press_global = None
        if was_tap:
            self.translate_requested.emit()
        else:
            self._save_geometry()
```

- [ ] **Step 4: 运行,确认通过**

Run: `pytest tests/test_translation_overlay.py tests/test_overlay_geometry.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add ui/translation_overlay.py tests/test_translation_overlay.py
git commit -m "feat(overlay): 轻点翻译 + 拖动/轻点手势区分 + 归位小按钮替代双击"
```

---

### Task 5: 主面板 — 翻译模式下拉

**Files:**
- Modify: `ui/main_window.py`
- Test: `tests/test_main_window_signals.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_main_window_signals.py` 末尾追加:

```python
def test_mode_combo_emits_mode_changed(app):
    from ui.main_window import MainWindow

    window = MainWindow(copy.deepcopy(DEFAULT_CONFIG))  # 默认 manual
    got = []
    window.mode_changed.connect(lambda m: got.append(m))
    window.mode_combo.setCurrentIndex(window.mode_combo.findData("auto"))
    assert got == ["auto"]
    assert window.mode_combo.currentData() == "auto"
```

- [ ] **Step 2: 运行,确认失败**

Run: `pytest tests/test_main_window_signals.py -v`
Expected: 新用例 FAIL(无 `mode_combo` / `mode_changed`)。

- [ ] **Step 3: 改 `ui/main_window.py`**

① 信号区(`lang_changed` 旁)增加:

```python
    mode_changed = pyqtSignal(str)            # manual | auto
```

② 「控制」区:在创建 `self.capture_btn` 之前插入模式选择行。把 `ctrl_group` 那段开头改为:

```python
        # 控制
        ctrl_group = QGroupBox("控制")
        ctrl = QVBoxLayout(ctrl_group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("翻译模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("手动", "manual")
        self.mode_combo.addItem("自动", "auto")
        midx = self.mode_combo.findData(self._config["trigger"].get("mode", "manual"))
        if midx >= 0:
            self.mode_combo.setCurrentIndex(midx)
        self.mode_combo.currentIndexChanged.connect(self._on_mode)
        mode_row.addWidget(self.mode_combo)
        ctrl.addLayout(mode_row)

        self.capture_btn = QPushButton("显示采集框")
```

(其余 `ctrl` 内容不变。)

③ 增加处理函数(放在 `_on_lang` 附近):

```python
    def _on_mode(self):
        self.mode_changed.emit(self.mode_combo.currentData())
```

④ 把底部提示文案那行改为:

```python
        hint = QLabel("手动:点译文框或 Alt+D 翻译当前画面;自动:画面停稳自动翻译")
```

- [ ] **Step 4: 运行,确认通过**

Run: `pytest tests/test_main_window_signals.py -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add ui/main_window.py tests/test_main_window_signals.py
git commit -m "feat(ui): 主面板新增翻译模式(手动/自动)下拉"
```

---

### Task 6: 接线 — main.py 串起来

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 改 detector 构造**

把 `main.py` 中的 detector 构造(原 `change_threshold=...`)替换为:

```python
    detector = ChangeDetector(
        stability_ms=config["detection"]["stability_ms"],
        stable_hamming=config["detection"]["stable_hamming"],
        change_hamming=config["detection"]["change_hamming"],
    )
```

- [ ] **Step 2: 改 worker 构造,加 get_auto**

在 `TranslationWorker(...)` 的参数里、`get_scale=...` 之后加一行:

```python
        get_auto=lambda: config["trigger"]["mode"] == "auto",
```

- [ ] **Step 3: 增加模式 / 手动翻译处理函数**

在 `on_translation` 定义之后、信号连接之前,加入:

```python
    def on_mode(mode):
        config["trigger"]["mode"] = mode
        overlay.set_mode(mode)
        save_config(CONFIG_PATH, config)
        main_window.update_status(
            "手动模式:点译文框或按 Alt+D 翻译" if mode == "manual"
            else "自动模式:画面停稳自动翻译"
        )

    def on_manual_translate():
        if worker.isRunning():
            worker.request_force()
        else:
            main_window.update_status("请先点'开始翻译'并框好区域", is_error=True)
```

- [ ] **Step 4: 连接信号 + 启动时设模式**

在 `main_window.lang_changed.connect(on_lang)` 附近加:

```python
    main_window.mode_changed.connect(on_mode)
    overlay.translate_requested.connect(on_manual_translate)
```

在 `main_window.show()` 之前加:

```python
    overlay.set_mode(config["trigger"]["mode"])
```

- [ ] **Step 5: 导入自检 + 全量测试**

Run: `python -c "import main"`
Expected: 无报错(仅执行顶层 import,不启动 GUI)。

Run: `pytest -q`
Expected: 全部 PASS(原有 + 新增,无回归)。

- [ ] **Step 6: 提交**

```bash
git add main.py
git commit -m "feat: 接线手动/自动模式切换与轻点翻译"
```

---

### Task 7: 收尾验证

- [ ] **Step 1: 全量测试 + 计划归档**

Run: `pytest -q`
Expected: 全绿。

- [ ] **Step 2: 确认未误提交密钥**

Run: `git status --porcelain && git ls-files | grep -i config.json || echo "config.json 未被跟踪 ✓"`
Expected: 工作区干净;`config.json` 未被 git 跟踪。

- [ ] **Step 3: 勾选本计划复选框并提交**

把本计划文件中已完成的 `- [ ]` 改为 `- [x]`,然后:

```bash
git add docs/superpowers/plans/2026-06-10-manual-trigger-mode-and-detection-tuning.md
git commit -m "docs: 勾选手动模式实现计划"
```

---

## 自检(写计划者复盘)

- **覆盖**:配置默认/迁移(T1)、汉明容差检测(T2)、手动空闲不截屏(T3)、轻点翻译+手势+归位按钮(T4)、模式下拉(T5)、接线(T6)、验证(T7)——对应 spec 全部章节。
- **类型一致**:`get_auto`、`_tick`、`translate_requested`、`redock_btn`、`set_mode`、`_placeholder`、`mode_combo`、`mode_changed`、`stable_hamming`/`change_hamming` 在定义与调用处命名一致。
- **无占位**:每步均给出完整可粘贴代码与确切命令/预期。
- **风险**:汉明默认 3/5 为启发式且可配置;手动模式为兜底可靠路径,不依赖检测调参。
