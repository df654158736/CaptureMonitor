# 实时游戏翻译悬浮框 — 重构设计

- 日期: 2026-06-09
- 状态: 已与用户确认,待写实现计划
- 目标平台: Windows 11
- 技术栈: Python 3.8+ / PyQt6

## 1. 背景与目标

项目最初是一个「屏幕区域文字变化监控器」:固定 2 秒轮询截图 → 本地 OCR(Tesseract/Paddle)→ `difflib` 比较前后文本 → 把变化写入历史。翻译功能(googletrans)是后期附加,且只挂在「写历史」这一步,实时显示路径根本不翻译。

新目标是一个 **可自定义位置的实时翻译悬浮框**,用于翻译 **游戏文本/对话框(英 → 中)**,要求 **快** 且 **准**。明确放弃本地 OCR(慢、依赖电脑配置),改用 **百度图片翻译合一 API**(一次网络往返完成 OCR + 翻译)。

### 已确认的关键决策

| 维度 | 选择 |
|---|---|
| 在线服务 | 百度 AI 开放平台(翻译开放平台 · 图片翻译 API) |
| 管线 | OCR + 翻译 **合一**(图片翻译 API,单次往返) |
| 场景 | 游戏文本 / 对话框 |
| 语言方向 | 英 → 中(可配置) |
| 触发 | **自动图像变化检测 + 全局热键** |
| 显示 | **独立可拖动悬浮框**(默认仅译文,可切原文+译文) |
| 插件系统 | 移除(YAGNI;保留 backend 抽象以便扩展) |
| 全局热键 | `keyboard` 库 |
| 历史 | 保留轻量「译文回看」面板 |

## 2. 设计原则

- **UI 永不阻塞**:所有截图、变化检测、网络调用放后台 `QThread`,通过 Qt 信号回主线程。
- **省 API**:本地廉价变化检测,内容不变完全不调 API;LRU 缓存让重复对话秒出。
- **准确优先**:修 DPI 坐标、防抖到稳定再翻译、显式语言方向、合一 API 带版面上下文。
- **模块单一职责**:纯逻辑(变化检测、缓存、后端客户端、配置)与 Qt/UI 解耦,便于单测。

## 3. 架构总览与数据流

```
QThread(后台,不阻塞 UI)
  每 ~120ms:
    mss 抓取选区(物理像素) ──► ChangeDetector
                                  │ 无变化 → 跳过(0 API)
                                  │ 变化中 → 等稳定
                                  ▼ 变化且稳定(防抖 ~400ms)
                              dHash ─► Cache 命中? ─是─► 直接出译文(0 API)
                                          │ 否
                                          ▼
                              百度图片翻译 API(from=en, to=zh)
                                          ▼
                              存 Cache + emit translation_ready(原文, 译文)
  热键按下: 跳过变化判定,强制翻译当前帧(仍走缓存)
                                          ▼
主线程: 译文悬浮框显示 + 历史追加
```

## 4. 模块规格

### 新增

#### `core/config.py`
- **职责**:读写本地 `config.json`,设置持久化。
- **内容**:百度 `appid`/`secret`、语言对、选区 `(x,y,w,h)`、触发模式、热键、悬浮框几何与透明度、采样间隔、防抖时长、变化阈值。
- **接口**:`load() -> Config`、`save(cfg)`;字段有默认值,缺失字段容错。
- **依赖**:标准库 `json`。`config.json` 加入 `.gitignore`。

#### `core/backends/base.py`
- **职责**:翻译后端抽象接口,便于将来接有道/腾讯/LLM。
- **接口**:
  ```python
  class TranslationResult:
      src_text: str          # 识别出的原文(全部拼接)
      dst_text: str          # 译文(全部拼接)
      segments: list         # [{src, dst, rect}], 供将来 AR 叠加
  class TranslationBackend(ABC):
      def translate_image(self, image_bytes: bytes, src: str, dst: str) -> TranslationResult: ...
      @property
      def name(self) -> str: ...
  ```
- **依赖**:无(纯接口)。

#### `core/backends/baidu_image.py`
- **职责**:百度图片翻译客户端,实现 `TranslationBackend`。
- **要点**:
  - 端点:`https://fanyi-api.baidu.com/api/trans/sdk/picture`,POST multipart/form-data。
  - 参数:`image`(二进制)、`from`、`to`、`appid`、`salt`、`cuid`、`mac`、`version=3`、`sign`。
  - 签名:`sign = MD5(appid + MD5(image_bytes_hex) + salt + cuid + mac + 密钥)`(全小写十六进制)。
  - 响应:`data.sumSrc`(原文)、`data.sumDst`(译文)、`data.content[]`(每段 `src/dst/rect`)。
  - 超时(默认 5s)、失败重试 1 次、错误码 → 明确异常信息(余额/QPS/密钥)。
- **依赖**:`requests`、`hashlib`。
- **注意**:实现时需对照百度当前官方文档核对签名算法与响应字段(可能更新),并用一个固定测试向量锁定签名。

#### `core/change_detector.py`
- **职责**:判断选区图像是否「变化后已稳定」(防抖)。
- **方法**:每帧把选区缩到 32×32 灰度;与上一帧算平均绝对差(MAD)。MAD > 阈值视为「变化中」并刷新「最后变化时刻」;距最后变化超过 `stability_ms`(默认 400ms)且与「上次已翻译帧」不同 → 触发 `CHANGED_AND_STABLE`。同时提供当前帧 dHash 供缓存键。
- **接口**:`feed(frame) -> Event`(`NO_CHANGE` / `CHANGING` / `STABLE_CHANGED`);`current_hash() -> str`。
- **依赖**:`numpy`、`Pillow`。纯逻辑,可单测。

#### `core/cache.py`
- **职责**:LRU 缓存,键 = 帧 dHash,值 = `TranslationResult`。重开同一段对话直接命中,0 API。
- **接口**:`get(hash)`、`put(hash, result)`;容量默认 128;汉明距离容忍可选(先精确匹配,YAGNI)。
- **依赖**:`collections.OrderedDict`。纯逻辑,可单测。

#### `core/worker.py`
- **职责**:编排管线的 `TranslationWorker`,运行在独立 `QThread`。
- **循环**:按 `sample_interval`(默认 120ms)抓取选区 → `ChangeDetector` → 命中缓存或调后端 → `emit translation_ready(src, dst)`。
- **热键**:外部触发 `force_translate()`,跳过变化判定,翻译当前帧(仍查缓存)。
- **信号**:`translation_ready(str, str)`、`status_changed(str)`、`error_occurred(str)`。
- **依赖**:`screen_capture`、`change_detector`、`cache`、后端、`config`。
- **线程**:后端网络调用在该线程内同步执行,不影响 UI;启停干净(stop 事件 + 线程退出)。

#### `ui/translation_overlay.py` (核心交付物)
- **职责**:无边框 / 置顶 / 半透明 / 可拖动 / 可缩放的译文悬浮框。
- **要点**:
  - `FramelessWindowHint | WindowStaysOnTopHint | Tool`,半透明背景。
  - 自定义拖动(顶部把手区域 mousePress/Move);右下角 resize grip。
  - 默认仅显示译文,字体随框尺寸自适应;可切「原文 + 译文」双行核对。
  - 顶部细工具条:拖动 / 透明度滑块 / 显隐原文 / 关闭。
  - 位置 / 大小 / 透明度写入 config,下次启动还原。
- **依赖**:PyQt6、`config`。

### 改造

#### `utils/screen_capture.py`
- 换用 `mss`(比 `pyautogui` 快很多,多屏更稳)。
- **修 DPI**:选区坐标是 Qt 逻辑坐标,截图需物理像素;用 `devicePixelRatio` 换算,避免缩放(125%/150%)下截错区域 / 糊图。
- 接口:`capture_region(x, y, w, h) -> PIL.Image`(物理像素)。

#### `ui/overlay_window.py`(选区器)
- 同样修 DPI 坐标转换,使 `region_selected` 发出的坐标与实际截图像素一致。

#### `ui/main_window.py`(控制面板)
- **去掉** OCR 引擎下拉。
- 新增:百度 `appid`/`secret` 输入(持久化)、语言对(默认 EN→ZH)、触发模式(自动/热键/两者)、热键绑定、灵敏度/防抖(进阶,可折叠)、显示/隐藏译文框、开始/停止、查看历史。
- 首次无密钥引导填写。

#### `ui/history_panel.py`
- 改为接收翻译结果(原文 + 译文)做「译文回看」,不再是变化监控日志。保留导出。

### 删除

- `core/ocr/`(`paddle_ocr.py` / `tesseract_ocr.py` / `windows_ocr.py` / `base.py`)。
- `core/translator.py`(googletrans / 旧 Baidu 文本)。
- `core/monitor.py`(变化监控逻辑由 `worker.py` 取代)。
- `plugins/`、`core/plugin_loader.py`(插件系统,YAGNI)。
- `install_tesseract.py` / `install_tesseract.bat`(本地 OCR 安装助手)。
- `requirements.txt`:移除 `paddleocr` / `paddlepaddle` / `pyautogui` / `pywin32`(如不再需要);新增 `mss` / `requests` / `numpy` / `keyboard`;保留 `PyQt6` / `Pillow`。

## 5. 配置 schema(`config.json`,gitignored)

```json
{
  "baidu": { "appid": "", "secret": "" },
  "lang": { "from": "en", "to": "zh" },
  "region": [0, 0, 0, 0],
  "trigger": { "mode": "auto+hotkey", "hotkey": "alt+d" },
  "detection": { "sample_interval_ms": 120, "stability_ms": 400, "change_threshold": 8 },
  "overlay": { "x": 100, "y": 100, "w": 480, "h": 160, "opacity": 0.85, "show_source": false }
}
```

## 6. 性能与准确性

**快**:① 本地变化检测 ~5–10ms,不变完全不调 API;② API 仅内容真变时触发,缓存让重复对话秒出;③ 全程后台线程,UI 不卡;④ 合一 API 单次往返。目标延迟 ≈ 对话稳定后 0.5–1s 出译文。

**准**:① 修 DPI → 不截错区 / 不糊图;② 防抖到稳定 → 不翻译打字机半截文字;③ 合一 API 带版面上下文 → 优于逐行;④ 显式 `en→zh`;⑤ 可选小字体 2× 放大预处理提升小字识别。

## 7. 并发模型

- 一个 `QThread` 跑 `TranslationWorker`:capture + detect + 缓存 + 网络。
- UI 线程只渲染,经 Qt 队列连接(信号)接收结果,线程安全。
- 全局热键回调(`keyboard` 库)线程 → 通过线程安全方式通知 worker `force_translate`(信号 / 线程安全标志 / `QMetaObject.invokeMethod`)。

## 8. 测试策略

- 先写测试(纯逻辑模块):
  - `change_detector`:构造两张图,断言 NO_CHANGE / CHANGING / STABLE_CHANGED 时序与防抖。
  - `cache`:LRU 淘汰、命中 / 未命中、哈希键。
  - `baidu_image`:用固定输入锁定签名算法;mock HTTP 验证响应解析与错误码处理。
  - `config`:load/save 往返、缺字段默认值容错。
- worker(线程 + Qt)、UI:以假后端 + 假截图做集成 / 冒烟测试,核心交互手动验证。

## 9. 风险与待核实

- **百度图片翻译 API 契约**:签名算法与响应字段需对照官方当前文档核对,并用测试向量锁定。
- **QPS / 配额**:免费额度与并发限制;失败需对用户给明确提示。
- **全局热键**:`keyboard` 在游戏全屏独占(exclusive fullscreen)下可能收不到键;窗口化 / 无边框窗口模式正常。必要时回退到 Win32 `RegisterHotKey`。
- **小字体识别**:部分游戏字体小 / 花哨,合一 API 也可能识别不全;放大预处理为可选缓解项。

## 10. 非目标(本期不做)

- 原位 AR 译文叠加(用 rect 覆盖原文)—— 留作未来增强,`segments` 已预留数据。
- 多后端切换 UI(接口已抽象,实现仅百度)。
- 多语言双向切换 UI(配置可改,UI 先做 EN→ZH)。
