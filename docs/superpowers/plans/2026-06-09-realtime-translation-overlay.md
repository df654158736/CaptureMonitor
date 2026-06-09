# 实时游戏翻译悬浮框 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 CaptureMonitor 从「区域文字变化监控器」重构成一个 Windows 11 上的实时游戏翻译悬浮框:拖一个采集框罩在游戏英文文字上,后台检测变化并调用有道图片翻译合一 API(`ocrtransapi`),译文显示在自动吸附其下方的悬浮框里。

**Architecture:** 纯逻辑(config / cache / change_detector / backend / pipeline / 几何换算)与 Qt/UI 解耦,全部可单测。截图 + 变化检测 + 网络调用跑在后台 `QThread`,经 Qt 信号回主线程,UI 永不阻塞。本地廉价变化检测 + 防抖 + LRU 缓存,内容不变完全不调 API。

**Tech Stack:** Python 3.8+ / PyQt6 / mss(截图)/ requests(HTTP)/ numpy + Pillow(图像)/ keyboard(全局热键)/ pytest(测试)。

---

## 文件结构

**新增**
- `core/config.py` — 读写 `config.json`,带默认值与深合并容错。
- `core/cache.py` — LRU 缓存(键 = 帧 dHash)。
- `core/change_detector.py` — 图像变化检测 + 防抖(MAD + dHash)。
- `core/backends/__init__.py`、`core/backends/base.py` — 后端抽象接口 + `TranslationResult`。
- `core/backends/youdao_image.py` — 有道图片翻译客户端(`ocrtransapi`,v1 MD5 签名)。
- `core/pipeline.py` — 纯编排:detector → cache → backend。
- `core/worker.py` — `TranslationWorker(QThread)`,薄封装。
- `core/hotkey.py` — 全局热键封装(keyboard)。
- `ui/capture_box.py` — 采集框(两态:调整 / 锁定穿透)。
- `ui/translation_overlay.py` — 译文悬浮框(吸附 / 跟随 / 可拖离)。
- `tests/` — 单测。

**改造**
- `utils/screen_capture.py` — 换 mss + DPI 物理像素换算。
- `ui/history_panel.py` — 改为译文回看(原文 + 译文)。
- `ui/main_window.py` — 去掉 OCR 下拉,新增密钥 / 语言 / 触发 / 采集框 / 译文框控制。
- `main.py` — 重新接线。
- `requirements.txt`、`.gitignore`、`README.md`。

**删除**
- `core/ocr/`、`core/translator.py`、`core/monitor.py`、`core/plugin_loader.py`、`plugins/`、`ui/overlay_window.py`、`ui/region_indicator.py`、`install_tesseract.py`、`install_tesseract.bat`。

---

## Task 1: 测试基建 + 依赖 + gitignore

**Files:**
- Create: `pytest.ini`
- Create: `requirements-dev.txt`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Create: `tests/__init__.py`

- [ ] **Step 1: 写 pytest.ini**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: 写 requirements.txt(替换全部内容)**

```
PyQt6>=6.4.0
Pillow>=9.0.0
numpy>=1.21.0
mss>=9.0.0
requests>=2.28.0
keyboard>=0.13.5
```

- [ ] **Step 3: 写 requirements-dev.txt**

```
-r requirements.txt
pytest>=7.0.0
```

- [ ] **Step 4: 把 config.json 加入 .gitignore**

在 `.gitignore` 末尾追加一行:

```
config.json
```

- [ ] **Step 5: 建空测试包**

创建 `tests/__init__.py`(空文件)。

- [ ] **Step 6: 安装依赖并确认 pytest 能跑**

Run: `pip install -r requirements-dev.txt && python -m pytest -q`
Expected: `no tests ran`(0 收集到,退出码 5 或提示无测试),不报导入错误。

- [ ] **Step 7: Commit**

```bash
git add pytest.ini requirements.txt requirements-dev.txt .gitignore tests/__init__.py
git commit -m "chore: 测试基建与依赖,改用在线服务技术栈"
```

---

## Task 2: 配置模块 `core/config.py`

**Files:**
- Create: `core/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
import json
from core.config import load_config, save_config, DEFAULT_CONFIG


def test_load_missing_returns_defaults(tmp_path):
    cfg = load_config(str(tmp_path / "nope.json"))
    assert cfg == DEFAULT_CONFIG
    assert cfg is not DEFAULT_CONFIG  # 必须是副本,不能共享引用


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "config.json")
    cfg = load_config(path)
    cfg["youdao"]["app_key"] = "abc"
    cfg["overlay"]["opacity"] = 0.5
    save_config(path, cfg)
    again = load_config(path)
    assert again["youdao"]["app_key"] == "abc"
    assert again["overlay"]["opacity"] == 0.5


def test_partial_file_merges_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"youdao": {"app_key": "x"}}), encoding="utf-8")
    cfg = load_config(str(path))
    assert cfg["youdao"]["app_key"] == "x"
    assert cfg["youdao"]["app_secret"] == ""     # 缺失字段用默认补齐
    assert cfg["lang"]["from"] == "en"           # 缺失整段用默认补齐


def test_corrupt_file_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_config(str(path)) == DEFAULT_CONFIG
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.config'`。

- [ ] **Step 3: 实现 `core/config.py`**

```python
"""应用配置:读写 config.json,带默认值与深合并容错。"""

import json
import os
from copy import deepcopy

DEFAULT_CONFIG = {
    "youdao": {"app_key": "", "app_secret": ""},
    "lang": {"from": "en", "to": "zh-CHS"},
    "capture": {"x": 0, "y": 0, "w": 0, "h": 0},
    "trigger": {"mode": "auto+hotkey", "hotkey": "alt+d"},
    "detection": {"sample_interval_ms": 120, "stability_ms": 400, "change_threshold": 8},
    "overlay": {
        "dock": "below", "detached": False,
        "x": 100, "y": 100, "w": 480, "h": 160,
        "opacity": 0.85, "show_source": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return deepcopy(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_CONFIG)
    return _deep_merge(DEFAULT_CONFIG, data)


def save_config(path: str, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS(4 passed)。

- [ ] **Step 5: Commit**

```bash
git add core/config.py tests/test_config.py
git commit -m "feat: 配置模块(默认值 + 深合并容错)"
```

---

## Task 3: LRU 缓存 `core/cache.py`

**Files:**
- Create: `core/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_cache.py
from core.cache import LRUCache


def test_put_get():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    assert c.get("a") == 1


def test_miss_returns_none():
    assert LRUCache().get("missing") is None


def test_eviction_beyond_capacity():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)          # 淘汰最久未用的 a
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_access_refreshes_lru_order():
    c = LRUCache(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1  # a 变最近使用
    c.put("c", 3)           # 淘汰 b 而不是 a
    assert c.get("a") == 1
    assert c.get("b") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_cache.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.cache'`。

- [ ] **Step 3: 实现 `core/cache.py`**

```python
"""按 dHash 缓存翻译结果的 LRU。"""

from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self._data: "OrderedDict[str, Any]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_cache.py -q`
Expected: PASS(4 passed)。

- [ ] **Step 5: Commit**

```bash
git add core/cache.py tests/test_cache.py
git commit -m "feat: LRU 缓存"
```

---

## Task 4: 变化检测 `core/change_detector.py`

**Files:**
- Create: `core/change_detector.py`
- Test: `tests/test_change_detector.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_change_detector.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.change_detector'`。

- [ ] **Step 3: 实现 `core/change_detector.py`**

```python
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
    return format(bits, "016x")


class ChangeDetector:
    def __init__(self, change_threshold: float = 8.0, stability_ms: int = 400):
        self.change_threshold = change_threshold
        self.stability_ms = stability_ms
        self._prev_small = None
        self._cur_hash = None
        self._last_change_at = None
        self._pending = False
        self._last_translated_hash = None

    def feed(self, frame: np.ndarray, now: float) -> str:
        small = _to_small_gray(frame)
        self._cur_hash = _dhash(frame)

        if self._prev_small is None:
            self._prev_small = small
            self._last_change_at = now
            self._pending = True
            return CHANGING

        mad = float(np.mean(np.abs(small - self._prev_small)))
        self._prev_small = small

        if mad > self.change_threshold:
            self._last_change_at = now
            self._pending = True
            return CHANGING

        if self._pending and (now - self._last_change_at) * 1000.0 >= self.stability_ms:
            self._pending = False
            if self._cur_hash != self._last_translated_hash:
                self._last_translated_hash = self._cur_hash
                return STABLE_CHANGED

        return NO_CHANGE

    def current_hash(self):
        return self._cur_hash

    def notify_translated(self, hash_value: str) -> None:
        """缓存命中或强制翻译后,标记该帧已翻译,避免重复触发。"""
        self._last_translated_hash = hash_value
        self._pending = False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_change_detector.py -q`
Expected: PASS(6 passed)。

- [ ] **Step 5: Commit**

```bash
git add core/change_detector.py tests/test_change_detector.py
git commit -m "feat: 图像变化检测 + 防抖"
```

---

## Task 5: 后端抽象 + 有道图片翻译 `core/backends/`

**Files:**
- Create: `core/backends/__init__.py`(空)
- Create: `core/backends/base.py`
- Create: `core/backends/youdao_image.py`
- Test: `tests/test_youdao_image.py`

> 注意:有道**图片翻译 `ocrtransapi`** 用的是 **v1 老版签名**:`sign = MD5(appKey + q + salt + appSecret)`,其中 `q = base64(图片字节)`,**用完整 q,不 truncate,无 curtime/signType**。这与有道 OCR(`ocrapi`)的 v3 SHA256+truncate+curtime 不同,别混。

- [ ] **Step 1: 写失败测试**

测试向量已用真实 MD5 算出(见对话中计算),非自证循环:
`MD5("youdaoAppKey" + "aGVsbG8gd29ybGQ=" + "FIXED-SALT" + "youdaoAppSecret") == 5d4db2cbc1155719ba0d894e5caadd03`,其中 `aGVsbG8gd29ybGQ= = base64(b"hello world")`。

```python
# tests/test_youdao_image.py
import base64
import pytest
from core.backends.base import TranslationResult
from core.backends.youdao_image import YoudaoImageTranslate, YoudaoImageError, build_sign


def test_build_sign_known_vector():
    q = base64.b64encode(b"hello world").decode("utf-8")  # aGVsbG8gd29ybGQ=
    sign = build_sign("youdaoAppKey", q, "FIXED-SALT", "youdaoAppSecret")
    assert sign == "5d4db2cbc1155719ba0d894e5caadd03"


def test_parse_success():
    payload = {
        "errorCode": "0",
        "lanFrom": "en", "lanTo": "zh-CHS",
        "resRegions": [
            {"context": "Hello", "tranContent": "你好", "boundingBox": "0,0,50,20"},
            {"context": "World", "tranContent": "世界", "boundingBox": "0,20,50,20"},
        ],
    }
    result = YoudaoImageTranslate._parse(payload)
    assert isinstance(result, TranslationResult)
    assert result.src_text == "Hello\nWorld"
    assert result.dst_text == "你好\n世界"
    assert result.segments[0] == {"src": "Hello", "dst": "你好", "rect": "0,0,50,20"}


def test_parse_error_code_raises():
    with pytest.raises(YoudaoImageError):
        YoudaoImageTranslate._parse({"errorCode": "108"})  # 108 = 应用ID不存在


def test_translate_without_creds_raises():
    backend = YoudaoImageTranslate(app_key="", app_secret="")
    with pytest.raises(YoudaoImageError):
        backend.translate_image(b"img", "en", "zh-CHS")


def test_translate_image_posts_correct_sign(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"errorCode": "0", "resRegions": [
                {"context": "Hi", "tranContent": "嗨", "boundingBox": "0,0,1,1"}]}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResp()

    monkeypatch.setattr("core.backends.youdao_image.requests.post", fake_post)

    backend = YoudaoImageTranslate(app_key="AK", app_secret="SK", salt_fn=lambda: "555")
    image = b"IMAGEBYTES"
    result = backend.translate_image(image, "en", "zh-CHS")

    q = base64.b64encode(image).decode("utf-8")
    expected_sign = build_sign("AK", q, "555", "SK")
    assert captured["url"] == "https://openapi.youdao.com/ocrtransapi"
    assert captured["data"]["sign"] == expected_sign
    assert captured["data"]["q"] == q
    assert captured["data"]["from"] == "en"
    assert captured["data"]["to"] == "zh-CHS"
    assert captured["data"]["type"] == "1"
    assert captured["data"]["appKey"] == "AK"
    assert result.dst_text == "嗨"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_youdao_image.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.backends'`。

- [ ] **Step 3: 实现 `core/backends/__init__.py`**

创建空文件 `core/backends/__init__.py`。

- [ ] **Step 4: 实现 `core/backends/base.py`**

```python
"""翻译后端抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TranslationResult:
    src_text: str
    dst_text: str
    segments: List[Dict[str, str]] = field(default_factory=list)  # [{src, dst, rect}]


class TranslationBackend(ABC):
    @abstractmethod
    def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
```

- [ ] **Step 5: 实现 `core/backends/youdao_image.py`**

```python
"""有道智云 · 图片翻译(ocrtransapi,OCR + 翻译合一)客户端。

文档:https://ai.youdao.com/DOCSIRMA/html/trans/api/tpfy/index.html
签名(v1):q = base64(image);sign = MD5(appKey + q + salt + appSecret)。
注意:此处用完整 q(不 truncate),无 curtime/signType —— 与 OCR 接口不同。
"""

import base64
import hashlib
import uuid
import requests

from .base import TranslationBackend, TranslationResult

API_URL = "https://openapi.youdao.com/ocrtransapi"


class YoudaoImageError(Exception):
    pass


def build_sign(app_key: str, q: str, salt: str, app_secret: str) -> str:
    sign_str = app_key + q + salt + app_secret
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


class YoudaoImageTranslate(TranslationBackend):
    def __init__(self, app_key: str, app_secret: str, timeout: float = 5.0, salt_fn=None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.timeout = timeout
        self._salt_fn = salt_fn or (lambda: str(uuid.uuid1()))

    @property
    def name(self) -> str:
        return "Youdao Image Translate"

    def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult:
        if not self.app_key or not self.app_secret:
            raise YoudaoImageError("有道 app_key/app_secret 未配置")

        q = base64.b64encode(image_bytes).decode("utf-8")
        salt = self._salt_fn()
        sign = build_sign(self.app_key, q, salt, self.app_secret)
        data = {
            "from": src, "to": dst, "type": "1", "q": q,
            "appKey": self.app_key, "salt": salt, "sign": sign,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            resp = requests.post(API_URL, data=data, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as e:
            raise YoudaoImageError(f"网络错误: {e}") from e
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> TranslationResult:
        code = str(payload.get("errorCode", ""))
        if code != "0":
            raise YoudaoImageError(f"有道返回错误 {code}")
        regions = payload.get("resRegions") or []
        segments = [
            {
                "src": r.get("context", ""),
                "dst": r.get("tranContent", ""),
                "rect": r.get("boundingBox", ""),
            }
            for r in regions
        ]
        src_text = "\n".join(s["src"] for s in segments)
        dst_text = "\n".join(s["dst"] for s in segments)
        return TranslationResult(src_text=src_text, dst_text=dst_text, segments=segments)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `python -m pytest tests/test_youdao_image.py -q`
Expected: PASS(5 passed)。

- [ ] **Step 7: Commit**

```bash
git add core/backends tests/test_youdao_image.py
git commit -m "feat: 有道图片翻译后端 + 抽象接口"
```

---

## Task 6: 截图 + DPI 换算 `utils/screen_capture.py`

**Files:**
- Modify: `utils/screen_capture.py`(整体重写)
- Test: `tests/test_screen_capture.py`

- [ ] **Step 1: 写失败测试(只测纯函数 physical_rect)**

```python
# tests/test_screen_capture.py
from utils.screen_capture import physical_rect


def test_physical_rect_scale_1():
    assert physical_rect(10, 20, 100, 50, 1.0) == (10, 20, 100, 50)


def test_physical_rect_scale_1_5():
    assert physical_rect(10, 20, 100, 50, 1.5) == (15, 30, 150, 75)


def test_physical_rect_rounds():
    assert physical_rect(0, 0, 33, 33, 1.25) == (0, 0, 41, 41)  # 41.25 -> 41
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_screen_capture.py -q`
Expected: FAIL，`ImportError: cannot import name 'physical_rect'`。

- [ ] **Step 3: 重写 `utils/screen_capture.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_screen_capture.py -q`
Expected: PASS(3 passed)。

- [ ] **Step 5: 手动冒烟(有显示器时)**

Run:
```bash
python -c "from utils.screen_capture import capture_region; im=capture_region(0,0,200,100); print(im.size, im.mode)"
```
Expected: 打印 `(200, 100) RGB`(WSL 无显示时可跳过,留待 Task 15 整体验证)。

- [ ] **Step 6: Commit**

```bash
git add utils/screen_capture.py tests/test_screen_capture.py
git commit -m "feat: mss 截图 + DPI 物理像素换算"
```

---

## Task 7: 编排管线 `core/pipeline.py`

**Files:**
- Create: `core/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_pipeline.py
import numpy as np
from core.pipeline import TranslationPipeline
from core.backends.base import TranslationResult

BLACK = np.zeros((32, 32, 3), dtype=np.uint8)
WHITE = np.full((32, 32, 3), 255, dtype=np.uint8)


class FakeBackend:
    def __init__(self):
        self.calls = 0

    @property
    def name(self):
        return "fake"

    def translate_image(self, image_bytes, src, dst):
        self.calls += 1
        return TranslationResult(src_text=f"src{self.calls}", dst_text=f"dst{self.calls}")


def make_pipeline(backend):
    return TranslationPipeline(backend, src="en", dst="zh-CHS", to_png=lambda f: b"png")


def test_no_translation_until_stable():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    assert pipe.process_frame(BLACK, now=0.0) is None   # 首帧 CHANGING
    assert backend.calls == 0


def test_translate_on_stable_change():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    pipe.process_frame(BLACK, now=0.0)
    result = pipe.process_frame(BLACK, now=0.5)         # STABLE_CHANGED
    assert result is not None
    assert result.dst_text == "dst1"
    assert backend.calls == 1


def test_cache_hit_skips_backend():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    pipe.process_frame(BLACK, now=0.0)
    pipe.process_frame(BLACK, now=0.5)                  # 翻译并缓存
    again = pipe.process_frame(BLACK, now=0.6, force=True)  # 同帧强制 → 命中缓存
    assert again.dst_text == "dst1"
    assert backend.calls == 1                           # 没有再调后端


def test_force_translates_immediately():
    backend = FakeBackend()
    pipe = make_pipeline(backend)
    result = pipe.process_frame(WHITE, now=0.0, force=True)  # 首帧强制
    assert result is not None
    assert backend.calls == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_pipeline.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'core.pipeline'`。

- [ ] **Step 3: 实现 `core/pipeline.py`**

```python
"""纯编排:变化检测 → 缓存 → 后端。无 Qt、无线程,可完整单测。"""

import io
from typing import Optional

import numpy as np
from PIL import Image

from core.cache import LRUCache
from core.change_detector import ChangeDetector, STABLE_CHANGED
from core.backends.base import TranslationBackend, TranslationResult


def _frame_to_png(frame: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(frame).save(buf, format="PNG")
    return buf.getvalue()


class TranslationPipeline:
    def __init__(self, backend: TranslationBackend, detector: ChangeDetector = None,
                 cache: LRUCache = None, src: str = "en", dst: str = "zh-CHS", to_png=None):
        self.backend = backend
        self.detector = detector or ChangeDetector()
        self.cache = cache or LRUCache()
        self.src = src
        self.dst = dst
        self._to_png = to_png or _frame_to_png

    def process_frame(self, frame: np.ndarray, now: float,
                      force: bool = False) -> Optional[TranslationResult]:
        event = self.detector.feed(frame, now)
        if not force and event != STABLE_CHANGED:
            return None

        h = self.detector.current_hash()
        cached = self.cache.get(h)
        if cached is not None:
            self.detector.notify_translated(h)
            return cached

        png = self._to_png(frame)
        result = self.backend.translate_image(png, self.src, self.dst)
        self.cache.put(h, result)
        self.detector.notify_translated(h)
        return result
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_pipeline.py -q`
Expected: PASS(4 passed)。

- [ ] **Step 5: 跑全量测试确认没有回归**

Run: `python -m pytest -q`
Expected: PASS(全部通过)。

- [ ] **Step 6: Commit**

```bash
git add core/pipeline.py tests/test_pipeline.py
git commit -m "feat: 翻译编排管线(检测→缓存→后端)"
```

---

## Task 8: 后台线程 `core/worker.py` + 全局热键 `core/hotkey.py`

UI/线程层,自动化测试价值低,以代码 + 手动冒烟为主。

**Files:**
- Create: `core/worker.py`
- Create: `core/hotkey.py`

- [ ] **Step 1: 实现 `core/worker.py`**

```python
"""后台翻译线程:循环截图 → 管线 → 信号回主线程。UI 永不阻塞。"""

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

    def __init__(self, pipeline, get_region, get_scale, sample_interval_ms: int = 120):
        super().__init__()
        self.pipeline = pipeline
        self.get_region = get_region   # () -> (x, y, w, h) 逻辑坐标 或 None
        self.get_scale = get_scale     # () -> float devicePixelRatio
        self.sample_interval_ms = sample_interval_ms
        self._running = False
        self._force = False

    def request_force(self):
        """热键触发:下一帧强制翻译。"""
        self._force = True

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            region = self.get_region()
            if region and region[2] > 0 and region[3] > 0:
                try:
                    px = physical_rect(*region, self.get_scale())
                    image = capture_region(*px)
                    frame = np.asarray(image.convert("RGB"))
                    force, self._force = self._force, False
                    result = self.pipeline.process_frame(frame, time.monotonic(), force=force)
                    if result is not None:
                        self.translation_ready.emit(result.src_text, result.dst_text)
                except Exception as e:  # 单帧失败不能拖垮线程
                    logger.error(f"worker tick 失败: {e}")
                    self.error_occurred.emit(str(e))
            self.msleep(self.sample_interval_ms)
```

- [ ] **Step 2: 实现 `core/hotkey.py`**

```python
"""全局热键封装(keyboard 库)。游戏占焦点时仍能触发(独占全屏可能失效)。"""

import logging

logger = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self):
        self._registered = None

    def register(self, hotkey: str, callback) -> bool:
        self.unregister()
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, callback)
            self._registered = hotkey
            logger.info(f"已注册全局热键: {hotkey}")
            return True
        except Exception as e:
            logger.warning(f"注册全局热键失败 ({hotkey}): {e}")
            return False

    def unregister(self):
        if self._registered:
            try:
                import keyboard
                keyboard.remove_hotkey(self._registered)
            except Exception:
                pass
            self._registered = None
```

- [ ] **Step 3: 导入冒烟**

Run: `python -c "import core.worker, core.hotkey; print('ok')"`
Expected: 打印 `ok`(无导入错误;keyboard 在 Linux 下导入即可,注册才需权限)。

- [ ] **Step 4: Commit**

```bash
git add core/worker.py core/hotkey.py
git commit -m "feat: 后台翻译线程 + 全局热键封装"
```

---

## Task 9: 译文悬浮框 `ui/translation_overlay.py`

**Files:**
- Create: `ui/translation_overlay.py`
- Test: `tests/test_overlay_geometry.py`(纯几何函数)

- [ ] **Step 1: 写失败测试(吸附几何)**

```python
# tests/test_overlay_geometry.py
from ui.translation_overlay import dock_rect_below


def test_dock_below_basic():
    # 采集框 (100,100,480,160),译文框高 120,间隙 6
    assert dock_rect_below(100, 100, 480, 160, overlay_h=120, gap=6) == (100, 266, 480, 120)


def test_dock_below_zero_gap():
    assert dock_rect_below(0, 0, 300, 50, overlay_h=80, gap=0) == (0, 50, 300, 80)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_overlay_geometry.py -q`
Expected: FAIL，`ImportError: cannot import name 'dock_rect_below'`。

- [ ] **Step 3: 实现 `ui/translation_overlay.py`**

```python
"""译文悬浮框:无边框/置顶/半透明/可拖动/可缩放。
默认 dock 在采集框正下方并跟随;用户拖动它即切为独立模式。
"""

import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizeGrip
from PyQt6.QtCore import Qt, QPoint, pyqtSignal

logger = logging.getLogger(__name__)


def dock_rect_below(cap_x, cap_y, cap_w, cap_h, overlay_h, gap=6):
    """采集框矩形 → 译文框吸附在其正下方的矩形(宽度跟随采集框)。"""
    return (cap_x, cap_y + cap_h + gap, cap_w, overlay_h)


class TranslationOverlay(QWidget):
    detached = pyqtSignal()  # 用户拖动 → 脱离吸附

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._drag_offset = None
        self._show_source = config["overlay"].get("show_source", False)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.src_label = QLabel("")
        self.src_label.setWordWrap(True)
        self.src_label.setStyleSheet("color: #b9c0c8; font-size: 13px;")
        self.src_label.setVisible(self._show_source)
        layout.addWidget(self.src_label)

        self.dst_label = QLabel("等待翻译…")
        self.dst_label.setWordWrap(True)
        self.dst_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        layout.addWidget(self.dst_label)

        grip = QSizeGrip(self)
        layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        ov = config["overlay"]
        self.setGeometry(ov["x"], ov["y"], ov["w"], ov["h"])
        self.setWindowOpacity(ov.get("opacity", 0.85))

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setBrush(QColor(20, 22, 26, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.end()

    def set_text(self, src: str, dst: str):
        if self._show_source:
            self.src_label.setText(src)
        self.dst_label.setText(dst or "(无文字)")

    def set_show_source(self, show: bool):
        self._show_source = show
        self.src_label.setVisible(show)

    def dock_to(self, cap_x, cap_y, cap_w, cap_h):
        """被采集框调用:吸附到采集框下方(独立模式下忽略)。"""
        if self._config["overlay"].get("detached"):
            return
        x, y, w, h = dock_rect_below(cap_x, cap_y, cap_w, cap_h, self.height())
        self.setGeometry(x, y, w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            if not self._config["overlay"].get("detached"):
                self._config["overlay"]["detached"] = True
                self.detached.emit()
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        self._save_geometry()

    def _save_geometry(self):
        g = self.geometry()
        ov = self._config["overlay"]
        ov["x"], ov["y"], ov["w"], ov["h"] = g.x(), g.y(), g.width(), g.height()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_overlay_geometry.py -q`
Expected: PASS(2 passed)。

- [ ] **Step 5: Commit**

```bash
git add ui/translation_overlay.py tests/test_overlay_geometry.py
git commit -m "feat: 译文悬浮框(吸附/跟随/可拖离)"
```

---

## Task 10: 采集框 `ui/capture_box.py`

**Files:**
- Create: `ui/capture_box.py`

UI 交互为主,手动验证。

- [ ] **Step 1: 实现 `ui/capture_box.py`**

```python
"""采集框:直接拖动/缩放,其几何即采集区域。
两态:调整态(可拖动缩放) / 锁定态(细边框 + 鼠标穿透)。
"""

import logging

from PyQt6.QtWidgets import QWidget, QSizeGrip
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor

logger = logging.getLogger(__name__)


class CaptureBox(QWidget):
    geometry_changed = pyqtSignal(int, int, int, int)  # x, y, w, h(逻辑坐标)

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._locked = False
        self._drag_offset = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(16, 16)

        cap = config["capture"]
        if cap["w"] > 0 and cap["h"] > 0:
            self.setGeometry(cap["x"], cap["y"], cap["w"], cap["h"])
        else:
            self.setGeometry(300, 300, 480, 120)

    def resizeEvent(self, event):
        self._grip.move(self.width() - 16, self.height() - 16)
        self._emit_geometry()
        super().resizeEvent(event)

    def moveEvent(self, event):
        self._emit_geometry()
        super().moveEvent(event)

    def _emit_geometry(self):
        g = self.geometry()
        cap = self._config["capture"]
        cap["x"], cap["y"], cap["w"], cap["h"] = g.x(), g.y(), g.width(), g.height()
        self.geometry_changed.emit(g.x(), g.y(), g.width(), g.height())

    def current_scale(self) -> float:
        handle = self.windowHandle()
        if handle and handle.screen():
            return handle.screen().devicePixelRatio()
        return 1.0

    def set_locked(self, locked: bool):
        """锁定态:鼠标穿透到游戏,只保留细边框标示。"""
        self._locked = locked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, locked)
        self._grip.setVisible(not locked)
        # 重新应用窗口标志后需要再次 show
        was_visible = self.isVisible()
        if was_visible:
            self.show()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._locked:
            pen = QPen(QColor(0, 200, 0, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        else:
            painter.fillRect(self.rect(), QColor(0, 150, 255, 40))
            pen = QPen(QColor(0, 150, 255, 230))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        painter.end()

    def mousePressEvent(self, event):
        if not self._locked and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
```

- [ ] **Step 2: 导入冒烟**

Run: `python -c "import ui.capture_box; print('ok')"`
Expected: 打印 `ok`。

- [ ] **Step 3: Commit**

```bash
git add ui/capture_box.py
git commit -m "feat: 采集框(调整/锁定穿透两态)"
```

---

## Task 11: 译文回看面板 `ui/history_panel.py`

**Files:**
- Modify: `ui/history_panel.py`(整体重写)

- [ ] **Step 1: 重写 `ui/history_panel.py`**

```python
"""译文回看面板:记录每次翻译(原文 + 译文),可导出。"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class HistoryPanel(QWidget):
    clear_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("译文回看")
        self.setMinimumSize(420, 320)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._count = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("译文回看")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        btns = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        btns.addWidget(self.clear_btn)
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self._on_export)
        btns.addWidget(self.export_btn)
        layout.addLayout(btns)

        self.status_label = QLabel("0 条记录")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def add_translation(self, src: str, dst: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.text_edit.append(f"[{ts}] {src}\n    [译] {dst}\n")
        self._count += 1
        self.status_label.setText(f"{self._count} 条记录")
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

    def clear(self):
        self.text_edit.clear()
        self._count = 0
        self.status_label.setText("0 条记录")

    def _on_clear(self):
        self.clear()
        self.clear_requested.emit()

    def _on_export(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出译文", "translations.txt", "文本文件 (*.txt);;所有文件 (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.text_edit.toPlainText())
                self.status_label.setText(f"已导出到 {filepath}")
            except OSError as e:
                self.status_label.setText(f"导出失败: {e}")

    def closeEvent(self, event):
        self.hide()
        event.ignore()
```

- [ ] **Step 2: 导入冒烟**

Run: `python -c "import ui.history_panel; print('ok')"`
Expected: 打印 `ok`。

- [ ] **Step 3: Commit**

```bash
git add ui/history_panel.py
git commit -m "refactor: 历史面板改为译文回看"
```

---

## Task 12: 控制面板 `ui/main_window.py`

**Files:**
- Modify: `ui/main_window.py`(整体重写)

- [ ] **Step 1: 重写 `ui/main_window.py`**

```python
"""主控制面板:密钥 / 语言 / 触发 / 采集框 / 译文框 / 开始停止。"""

import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    show_capture_requested = pyqtSignal()
    lock_toggled = pyqtSignal(bool)           # True=锁定开始, False=解锁停止
    show_overlay_requested = pyqtSignal(bool)
    view_history_requested = pyqtSignal()
    clear_history_requested = pyqtSignal()
    creds_changed = pyqtSignal(str, str)      # app_key, app_secret
    lang_changed = pyqtSignal(str, str)       # from, to

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self.setWindowTitle("实时翻译悬浮框")
        self.setMinimumSize(360, 380)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 有道密钥
        cred_group = QGroupBox("有道图片翻译密钥")
        cred_form = QFormLayout(cred_group)
        self.appkey_edit = QLineEdit(self._config["youdao"]["app_key"])
        self.secret_edit = QLineEdit(self._config["youdao"]["app_secret"])
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.appkey_edit.editingFinished.connect(self._on_creds)
        self.secret_edit.editingFinished.connect(self._on_creds)
        cred_form.addRow("应用ID:", self.appkey_edit)
        cred_form.addRow("密钥:", self.secret_edit)
        layout.addWidget(cred_group)

        # 语言方向
        lang_group = QGroupBox("语言方向")
        lang_layout = QHBoxLayout(lang_group)
        self.from_combo = QComboBox()
        self.from_combo.addItem("英文", "en")
        self.from_combo.addItem("日文", "jp")
        self.from_combo.addItem("自动", "auto")
        self.to_combo = QComboBox()
        self.to_combo.addItem("中文", "zh-CHS")
        self.from_combo.currentIndexChanged.connect(self._on_lang)
        self.to_combo.currentIndexChanged.connect(self._on_lang)
        lang_layout.addWidget(self.from_combo)
        lang_layout.addWidget(QLabel("→"))
        lang_layout.addWidget(self.to_combo)
        layout.addWidget(lang_group)

        # 控制
        ctrl_group = QGroupBox("控制")
        ctrl = QVBoxLayout(ctrl_group)
        self.capture_btn = QPushButton("显示采集框")
        self.capture_btn.setCheckable(True)
        self.capture_btn.toggled.connect(self._on_capture_toggle)
        ctrl.addWidget(self.capture_btn)

        self.start_btn = QPushButton("开始翻译")
        self.start_btn.setCheckable(True)
        self.start_btn.toggled.connect(self._on_start_toggle)
        ctrl.addWidget(self.start_btn)

        self.overlay_btn = QPushButton("显示译文框")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.setChecked(True)
        self.overlay_btn.toggled.connect(self.show_overlay_requested.emit)
        ctrl.addWidget(self.overlay_btn)

        self.history_btn = QPushButton("查看译文回看")
        self.history_btn.clicked.connect(self.view_history_requested.emit)
        ctrl.addWidget(self.history_btn)
        layout.addWidget(ctrl_group)

        hint = QLabel("热键 Alt+D:立即翻译当前画面")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)

        self.status_label = QLabel("就绪 — 请填密钥并拖动采集框到游戏文字上")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _on_creds(self):
        self.creds_changed.emit(self.appkey_edit.text().strip(), self.secret_edit.text().strip())

    def _on_lang(self):
        self.lang_changed.emit(self.from_combo.currentData(), self.to_combo.currentData())

    def _on_capture_toggle(self, checked):
        self.capture_btn.setText("隐藏采集框" if checked else "显示采集框")
        if checked:
            self.show_capture_requested.emit()

    def _on_start_toggle(self, checked):
        self.start_btn.setText("停止翻译" if checked else "开始翻译")
        self.lock_toggled.emit(checked)
        self.update_status("翻译中…" if checked else "已停止")

    def update_status(self, message: str, is_error: bool = False):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: red;" if is_error else "color: green;")

    def closeEvent(self, event):
        self.lock_toggled.emit(False)
        event.accept()
```

- [ ] **Step 2: 导入冒烟**

Run: `python -c "import ui.main_window; print('ok')"`
Expected: 打印 `ok`。

- [ ] **Step 3: Commit**

```bash
git add ui/main_window.py
git commit -m "refactor: 主控制面板改为翻译框配置"
```

---

## Task 13: 接线 `main.py`

**Files:**
- Modify: `main.py`(整体重写)

- [ ] **Step 1: 重写 `main.py`**

```python
"""实时翻译悬浮框 — 程序入口。"""

import os
import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.config import load_config, save_config
from core.backends.youdao_image import YoudaoImageTranslate
from core.change_detector import ChangeDetector
from core.cache import LRUCache
from core.pipeline import TranslationPipeline
from core.worker import TranslationWorker
from core.hotkey import HotkeyManager
from ui.main_window import MainWindow
from ui.capture_box import CaptureBox
from ui.translation_overlay import TranslationOverlay
from ui.history_panel import HistoryPanel

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    config = load_config(CONFIG_PATH)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("RealtimeTranslate")

    # 后端 + 管线
    backend = YoudaoImageTranslate(config["youdao"]["app_key"], config["youdao"]["app_secret"])
    detector = ChangeDetector(
        change_threshold=config["detection"]["change_threshold"],
        stability_ms=config["detection"]["stability_ms"],
    )
    pipeline = TranslationPipeline(
        backend, detector=detector, cache=LRUCache(),
        src=config["lang"]["from"], dst=config["lang"]["to"],
    )

    # UI
    main_window = MainWindow(config)
    capture_box = CaptureBox(config)
    overlay = TranslationOverlay(config)
    history = HistoryPanel()

    # Worker
    worker = TranslationWorker(
        pipeline,
        get_region=lambda: (config["capture"]["x"], config["capture"]["y"],
                            config["capture"]["w"], config["capture"]["h"]),
        get_scale=capture_box.current_scale,
        sample_interval_ms=config["detection"]["sample_interval_ms"],
    )

    # 热键
    hotkeys = HotkeyManager()
    hotkeys.register(config["trigger"]["hotkey"], worker.request_force)

    # ---- 接线 ----
    def on_creds(app_key, app_secret):
        config["youdao"]["app_key"] = app_key
        config["youdao"]["app_secret"] = app_secret
        backend.app_key, backend.app_secret = app_key, app_secret
        save_config(CONFIG_PATH, config)

    def on_lang(src, dst):
        config["lang"]["from"], config["lang"]["to"] = src, dst
        pipeline.src, pipeline.dst = src, dst
        save_config(CONFIG_PATH, config)

    def on_capture_geometry(x, y, w, h):
        overlay.dock_to(x, y, w, h)
        save_config(CONFIG_PATH, config)

    def on_lock(locked):
        if locked:
            if not config["youdao"]["app_key"] or not config["youdao"]["app_secret"]:
                main_window.update_status("请先填写有道应用ID 和密钥", is_error=True)
                main_window.start_btn.setChecked(False)
                return
            capture_box.set_locked(True)
            if not worker.isRunning():
                worker.start()
        else:
            worker.stop()
            worker.wait(2000)
            capture_box.set_locked(False)

    def on_translation(src, dst):
        overlay.set_text(src, dst)
        history.add_translation(src, dst)

    main_window.creds_changed.connect(on_creds)
    main_window.lang_changed.connect(on_lang)
    main_window.show_capture_requested.connect(capture_box.show)
    main_window.lock_toggled.connect(on_lock)
    main_window.show_overlay_requested.connect(
        lambda show: overlay.setVisible(show)
    )
    main_window.view_history_requested.connect(history.show)
    main_window.clear_history_requested.connect(history.clear)

    capture_box.geometry_changed.connect(on_capture_geometry)
    worker.translation_ready.connect(on_translation)
    worker.error_occurred.connect(lambda m: main_window.update_status(f"错误: {m}", is_error=True))

    # 初始吸附 + 显示
    cap = config["capture"]
    if cap["w"] > 0:
        overlay.dock_to(cap["x"], cap["y"], cap["w"], cap["h"])
    main_window.show()
    overlay.show()

    def cleanup():
        worker.stop()
        worker.wait(2000)
        hotkeys.unregister()
        save_config(CONFIG_PATH, config)

    app.aboutToQuit.connect(cleanup)
    logger.info("实时翻译悬浮框已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 导入冒烟**

Run: `python -c "import main; print('ok')"`
Expected: 打印 `ok`(无导入错误)。

- [ ] **Step 3: 跑全量单测确认无回归**

Run: `python -m pytest -q`
Expected: PASS(全部通过)。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: 接线实时翻译主流程"
```

---

## Task 14: 清理旧代码 + 文档

**Files:**
- Delete: `core/ocr/`、`core/translator.py`、`core/monitor.py`、`core/plugin_loader.py`、`plugins/`、`ui/overlay_window.py`、`ui/region_indicator.py`、`install_tesseract.py`、`install_tesseract.bat`
- Modify: `README.md`

- [ ] **Step 1: 删除旧模块**

```bash
git rm -r core/ocr plugins
git rm core/translator.py core/monitor.py core/plugin_loader.py
git rm ui/overlay_window.py ui/region_indicator.py
git rm install_tesseract.py install_tesseract.bat
```

- [ ] **Step 2: 确认没有残留引用**

Run: `grep -rn -E "import (ocr|monitor|translator|plugin_loader|overlay_window|region_indicator)|from core.ocr|from core.monitor|from core.translator|from core.plugin_loader|from ui.overlay_window|from ui.region_indicator" --include="*.py" .`
Expected: 无输出(没有任何残留引用)。

- [ ] **Step 3: 全量单测 + 入口导入**

Run: `python -m pytest -q && python -c "import main; print('ok')"`
Expected: 测试全过 + 打印 `ok`。

- [ ] **Step 4: 重写 README.md**

```markdown
# 实时翻译悬浮框 (CaptureMonitor)

Windows 11 上的实时游戏翻译工具:拖一个采集框罩在游戏英文文字上,自动识别变化并通过**有道图片翻译合一 API(`ocrtransapi`)**翻译,译文显示在自动吸附其下方的悬浮框里。

## 特性

- **采集框**:可拖动/缩放,直接罩在要翻译的文字上;开始后变细边框、鼠标穿透(不挡游戏)。
- **译文悬浮框**:默认吸附在采集框下方并跟随;可拖离自由摆放、可调透明度、可显示原文。
- **快**:后台线程截图,本地变化检测 + 防抖,内容不变不调 API;LRU 缓存让重复对话秒出;UI 永不卡顿。
- **准**:DPI 物理像素截图,合一 API 带版面上下文,显式英→中。
- **触发**:自动检测画面稳定变化,或按热键 `Alt+D` 立即翻译。

## 安装

```bash
pip install -r requirements.txt
```

## 使用

1. 到[有道智云](https://ai.youdao.com/)开通**图片翻译**服务,拿到应用ID 和密钥。
2. 运行 `python main.py`,在控制面板填入应用ID 和密钥。
3. 点「显示采集框」,把采集框拖到游戏文字上、调好大小。
4. 点「开始翻译」。译文出现在采集框下方;按 `Alt+D` 可手动刷新。

## 配置

设置存于 `config.json`(已 gitignore,含密钥,勿提交)。

## 开发

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## License

MIT
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: 删除本地 OCR/监控/插件旧代码,更新 README"
```

---

## Task 15: 端到端手动验证(在 Windows 11 上)

> 自动化测试覆盖纯逻辑;以下是必须在真实 Win11 + 真实有道密钥下走一遍的手动验收。

- [ ] **Step 1: 启动**

Run: `python main.py`
Expected: 控制面板出现;译文框出现并显示「等待翻译…」。

- [ ] **Step 2: 填密钥 → 持久化**

操作:填入真实 APP ID / 密钥,焦点移开;关掉程序再开。
Expected: 重开后密钥仍在(`config.json` 已保存)。

- [ ] **Step 3: 采集框拖放 + 译文框跟随**

操作:点「显示采集框」,拖动采集框。
Expected: 译文框始终吸附在采集框正下方一起移动;拖动译文框后它脱离、不再跟随。

- [ ] **Step 4: 实时翻译(自动)**

操作:把采集框罩在一段英文(网页/记事本/游戏)上,点「开始翻译」。
Expected: 约 0.5–1s 后译文框显示中文;采集框变绿色细边框且鼠标可穿透点到下层。

- [ ] **Step 5: 缓存 + 防抖**

操作:让英文内容不变,观察日志;再切回之前出现过的同一段文字。
Expected: 内容不变时不刷新、日志无新的 API 调用;重现旧文字时秒出(缓存命中)。

- [ ] **Step 6: 热键**

操作:切到游戏窗口焦点,按 `Alt+D`。
Expected: 立即翻译当前采集框画面(独占全屏游戏若无效,见 spec 风险项,改用窗口化)。

- [ ] **Step 7: DPI 正确性**

操作:在系统缩放 125%/150% 的显示器上重复 Step 4。
Expected: 截取的是采集框框住的内容(不偏移、不糊),译文正确。

- [ ] **Step 8: 错误处理**

操作:故意填错密钥后开始翻译。
Expected: 状态栏/译文框给出明确错误提示,程序不崩溃。

- [ ] **Step 9: 译文回看 + 退出**

操作:点「查看译文回看」看历史;关闭主窗口。
Expected: 历史列出原文+译文;退出时线程干净停止、`config.json` 保存采集框/译文框位置。

- [ ] **Step 10: 最终提交(如有手动修复)**

```bash
git add -A
git commit -m "fix: 端到端验证修复"
```

---

## Self-Review(写完计划后的自查结果)

- **Spec 覆盖**:配置✓(T2)、缓存✓(T3)、变化检测/防抖✓(T4)、有道合一后端✓(T5)、mss+DPI✓(T6)、编排管线✓(T7)、后台线程✓(T8)、全局热键✓(T8)、译文悬浮框+吸附跟随✓(T9)、采集框两态✓(T10)、译文回看✓(T11)、控制面板✓(T12)、接线✓(T13)、删除旧代码+README✓(T14)、DPI/缓存/热键/错误处理的端到端验证✓(T15)。原位 AR 叠加属 spec 非目标,未排任务(正确)。
- **占位符扫描**:无 TBD/TODO;每个代码步骤含完整代码,每个测试步骤含完整断言。
- **类型/命名一致**:`TranslationResult(src_text/dst_text/segments)`、`ChangeDetector.feed/current_hash/notify_translated`、`TranslationPipeline.process_frame(frame, now, force)`、`build_sign(app_key, q, salt, app_secret)`、`YoudaoImageTranslate(app_key, app_secret)`、`physical_rect(x,y,w,h,scale)`、`dock_rect_below(...)`、`TranslationWorker.request_force/stop`、`CaptureBox.geometry_changed/current_scale/set_locked` 在各任务间一致。
