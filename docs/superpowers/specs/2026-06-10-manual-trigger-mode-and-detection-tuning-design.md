# 设计:手动点击翻译模式 + 自动检测优化

日期:2026-06-10
状态:已确认,待转实现计划

## 背景与问题

实时翻译悬浮框当前只有「自动检测 + 热键」一种触发方式。实测中自动检测的主要症状是**该翻译时不翻译(漏触发)**:

- 采集区内只要有持续动画(光标闪烁、UI 呼吸、粒子、视频背景),帧的 dHash 几乎每帧都在变,永远达不到「连续 stability_ms 完全相等」的稳定条件,于是新对话出现也不触发。
- 感知哈希(8×8 dHash)较粗,偶发新内容与上一帧碰撞为同一 hash,被当作「已翻译」跳过。

这类问题对游戏场景几乎无法靠调参根治,所以引入一个**可靠的手动触发模式**作为默认,同时对自动检测做一次有针对性的容差优化(best-effort)。

## 目标

1. 新增「翻译模式」开关:**自动 / 手动**,二选一互斥,**默认手动**。
2. 手动模式:**轻点译文框**(或热键 Alt+D)触发一次「截当前画面 + 翻译」。空闲时零截屏开销。
3. 自动模式:修漏触发 —— 把变化检测从「dHash 完全相等」改为**汉明距离容差**。
4. 译文框手势重构,消除轻点/拖动/回靠之间的冲突。

非目标:不改后端(有道/火山)、缓存、截图、磁吸吸附逻辑本身。

## 架构改动总览

集中在 6 个文件,互不耦合,可独立测试:

| 文件 | 改动 |
|---|---|
| `core/config.py` | `trigger.mode` 默认改 `"manual"`;新增 `detection.stable_hamming` / `detection.change_hamming`;旧值 `"auto+hotkey"` 归一化迁移 |
| `core/change_detector.py` | 稳定/变化判定从精确相等改为汉明距离容差 |
| `core/worker.py` | 新增 `get_auto` 回调;手动模式空闲不截屏,仅在 force 时截一帧翻译一次 |
| `ui/translation_overlay.py` | 新增 `translate_requested` 信号;手势重构;回靠改小按钮;模式占位文案 |
| `ui/main_window.py` | 新增「翻译模式」下拉 + `mode_changed` 信号;更新提示文案 |
| `main.py` | 接线:detector 新参数、worker `get_auto`、译文框轻点 → force、模式切换落盘 |

## 详细设计

### 1. 配置(core/config.py)

`DEFAULT_CONFIG` 变更:

```python
"trigger": {"mode": "manual", "hotkey": "alt+d"},   # mode: manual | auto
"detection": {
    "sample_interval_ms": 120,
    "stability_ms": 400,
    "change_threshold": 8,    # 保留,仅诊断
    "stable_hamming": 3,      # 相邻两帧 dHash 汉明距离 ≤ 此值视为"没动"
    "change_hamming": 5,      # 稳定内容与上次已翻译汉明距离 ≥ 此值才算"换了"
},
```

`load_config` 在 `_deep_merge` 之后加一步归一化(否则旧 config.json 里的 `"auto+hotkey"` 会被深合并保留):

```python
mode = merged["trigger"]["mode"]
if mode not in ("manual", "auto"):
    merged["trigger"]["mode"] = "auto" if "auto" in mode else "manual"
```

即:`"auto+hotkey"` → `"auto"`;`"hotkey"`/其它未知 → `"manual"`。

### 2. 变化检测(core/change_detector.py)

`_dhash` 保持不变(仍返回 `"{mean:02x}{bits:016x}"`,18 个十六进制字符,供缓存键去重)。新增两个纯函数:

```python
def _bits_of(hash_str: str) -> int:   # 整串(含均值字节)= 72 位
    return int(hash_str, 16)

def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
```

**为什么含均值字节**:纯色图(如全黑 vs 全白)的 64 位 dHash 都是全 0,只有前导均值字节能区分它们。若只比后 64 位,亮度截然不同的两帧会被判为"没动",漏触发。所以汉明距离对整串(8 位均值 + 64 位 dHash = 72 位)计算。代价:纯亮度漂移最多贡献 8 位距离;对文字内容,dHash 位变化占主导,可接受。

`ChangeDetector` 重写为「锚点 + 汉明容差」:

- `__init__(stability_ms=400, stable_hamming=3, change_hamming=5)`(保留 `change_threshold` 可选,仅诊断)。
- 状态:`_cur_hash`(最新帧全串,供 `current_hash()`/缓存)、`_anchor_bits`、`_anchor_at`、`_last_translated_bits`、`last_mad`(诊断)。
- `feed(frame, now)`:
  1. 算 `h`(全串)与 `bits`;更新 `self._cur_hash = h`(始终是最新帧,force 翻译时缓存键正确);算诊断 MAD。
  2. 无锚点 → 设锚点 = bits、`_anchor_at = now`,返回 `CHANGING`。
  3. `_hamming(bits, _anchor_bits) > stable_hamming` → 画面在动:锚点重置为 bits、刷新计时,返回 `CHANGING`。
  4. 否则在容差内(画面"停住"):若 `(now - _anchor_at)*1000 >= stability_ms`:
     - `_last_translated_bits is None` 或 `_hamming(_anchor_bits, _last_translated_bits) >= change_hamming` → **自标记** `_last_translated_bits = _anchor_bits` 后返回 `STABLE_CHANGED`。
     - 否则 `NO_CHANGE`。
  5. 其余 `NO_CHANGE`。
- `feed` 触发 `STABLE_CHANGED` 时**自标记** `_last_translated_bits`(与现版本一致,保证同一稳定窗口不反复触发,即使调用方未调 `notify_translated`)。
- `notify_translated(hash_str)`:`self._last_translated_bits = _bits_of(hash_str)` —— 供 **force/缓存命中** 路径标记(这些路径 feed 未返回 STABLE_CHANGED,但确实翻译/返回了译文,需标记以免自动模式随后重复触发同一内容)。
- `current_hash()`:返回 `_cur_hash`(不变)。

要点:汉明容差让"轻微抖动的画面"也能算稳定 → 新对话停下时能触发(修漏触发);`change_hamming` 门槛让纯抖动不会反复触发。

### 3. 后台线程(core/worker.py)

- 新增构造参数 `get_auto`(`() -> bool`,读 `config["trigger"]["mode"] == "auto"`)。
- `run()` 循环顶部先取 force 与 auto:
  ```python
  force, self._force = self._force, False
  auto = self.get_auto()
  if not force and not auto:
      self.msleep(self.sample_interval_ms)   # 手动模式空闲:不截屏、不检测
      continue
  ```
  其余(取 region、截图、心跳、`process_frame(frame, now, force=force)`)保持现状。
- 效果:手动模式平时零截屏;点击/热键置 `_force` 后,下一轮截一帧当前画面、`force=True` 绕过检测翻译一次,然后回到空闲。
- 心跳/`debug_capture.png`/首帧日志只在自动或被 force 时发生,符合预期。

### 4. 译文框(ui/translation_overlay.py)

- 新增 `translate_requested = pyqtSignal()`。
- 手势(移动阈值 `TAP_MOVE_TOLERANCE = 4` 逻辑像素):
  - `mousePressEvent`:记 `_drag_offset` 与按下时全局坐标 `_press_global`,`_moved = False`。
  - `mouseMoveEvent`:若相对按下点位移 > 阈值则 `_moved = True`,再走原拖动/磁吸逻辑。
  - `mouseReleaseEvent`:`_moved == False` → 视为轻点 → `translate_requested.emit()`;否则 `_save_geometry()`。重置 `_drag_offset`。
- **移除 `mouseDoubleClickEvent` 回靠**,改为右下角小按钮:
  - 一个子 `QPushButton`(文案 `📌`,约 24×24,半透明样式),`resizeEvent` 中定位到右上角;`clicked → redock()`。
  - 仅在脱离吸附(`detached==True`)时 `show()`,吸附/回靠后 `hide()`。在 `dock_to`(成功吸附)、`redock()` 里 `hide()`;在 `mouseMoveEvent` 判定脱离处 `show()`。
- 模式占位文案:新增 `set_mode(mode)`,存 `_mode`;维护 `_has_text`(`set_text` 置 True)。未出过译文时,`dst_label` 显示「点此翻译」(manual)/「等待翻译…」(auto);切换模式时若仍是占位则更新。
- `QSizeGrip` 与回靠按钮各自处理自身鼠标事件,不会被误判为框体轻点。

### 5. 主面板(ui/main_window.py)

- 新增 `mode_changed = pyqtSignal(str)`(`"manual"` | `"auto"`)。
- 「控制」区顶部加一行:`QLabel("翻译模式")` + `QComboBox`(项:手动→`manual`、自动→`auto`),默认取 `config["trigger"]["mode"]`,`currentIndexChanged → 发 mode_changed`。
- 底部提示文案改为:手动模式提示「点译文框或按 Alt+D 翻译当前画面」;两模式通用说明热键始终可用。

### 6. 接线(main.py)

- 构造 detector:
  ```python
  detector = ChangeDetector(
      stability_ms=config["detection"]["stability_ms"],
      stable_hamming=config["detection"]["stable_hamming"],
      change_hamming=config["detection"]["change_hamming"],
  )
  ```
- 构造 worker 增加 `get_auto=lambda: config["trigger"]["mode"] == "auto"`。
- `overlay.translate_requested` → `on_manual_translate`:`worker.isRunning()` 则 `worker.request_force()`,否则状态栏提示「请先点'开始翻译'并框好区域」。
- `main_window.mode_changed` → `on_mode(mode)`:写 `config["trigger"]["mode"]`、`save_config`、`overlay.set_mode(mode)`、状态栏提示当前模式。
- 启动时 `overlay.set_mode(config["trigger"]["mode"])`。
- 热键路径不变(已是 `worker.request_force`),手动/自动模式都生效。

## 交互流程(手动模式,默认)

1. 显示采集框 → 拖到游戏文字上。
2. 点「开始翻译」=「布防」:锁定采集框 + 启动 worker(空闲不截屏)。
3. **轻点译文框** 或按 **Alt+D** → 截当前画面翻译一次,译文显示。
4. 拖动译文框移动;脱离后点右下角 📌 归位。

自动模式:第 2 步后,画面停稳即自动翻译(汉明容差判定);轻点/热键仍可随时补一刀。

## 测试

纯逻辑(无 Qt):
- `_hamming` / `_bits_of` 正确性。
- `ChangeDetector`:① 抖动(每帧汉明 ≤ stable_hamming)能在 stability_ms 后触发一次;② 抖动后 `notify_translated` 标记,不再反复触发;③ 与上次仅差 < change_hamming 的内容不触发;④ 差 ≥ change_hamming 的新内容必触发;⑤ 持续大幅变化(滚动)期间不触发、停下后触发。
- `config`:默认 `mode == "manual"`;旧 `"auto+hotkey"` 归一化为 `"auto"`;未知值归一化为 `"manual"`;新 detection 键存在。

Qt offscreen(`QT_QPA_PLATFORM=offscreen`):
- 译文框:轻点(press→release 不移动)发 `translate_requested`;拖动(移动 > 阈值)不发、且保存几何;回靠按钮 `clicked` 调 `redock` 且仅脱离时可见。
- `set_mode` 切换占位文案。

线程门控:
- worker `get_auto=False` 且无 force 时不调用 `get_region`(用会抛异常的桩验证未截屏);置 force 后调用一次 `process_frame(force=True)`。

## 风险与权衡

- 汉明容差是启发式:`stable_hamming` 太大可能把"真的在变"误判为稳定;太小仍漏触发。默认 3/5 偏保守,作为可调配置项暴露。手动模式不依赖它,是兜底可靠路径。
- 回靠从双击改按钮:多一个可见控件,但换来手势零歧义、轻点零延迟,符合"点框即翻译"的直觉。
- 手动模式下「开始翻译」语义变为「布防/撤防」而非持续翻译;沿用原按钮,提示文案承担解释。
