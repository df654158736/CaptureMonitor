# Proposal: CaptureMonitor Application

## Why

需要一款 Windows 桌面工具来监控屏幕任意区域的文字变化。现有工具要么过于复杂，要么无法灵活地监控跨应用程序的内容。用户希望能够简单地拖动一个框选区域，实时识别其中的文字，并在文字发生变化时得到通知。

典型使用场景包括：
- 监控视频字幕变化
- 监控股票软件的数值变化
- 监控日志输出
- 监控游戏中的动态信息

## What Changes

创建一个新的桌面应用程序 **CaptureMonitor**，包含以下核心功能：

- **全屏框选系统**: 独立的半透明覆盖层，支持在屏幕任意位置拖动创建监控区域
- **OCR 文字识别**: 支持 PaddleOCR 和 Windows OCR API 两种引擎，用户可选择
- **变化检测**: 定期扫描监控区域，检测文字变化并记录
- **历史记录面板**: 可拖动的独立面板，显示监控历史（最多 1000 条），支持清空和导出
- **插件系统**: 简单的 Python 文件约定式插件，用于扩展不同场景的处理逻辑
- **控制窗口**: 主控制面板，可最小化，提供 OCR 选择、插件选择、间隔设置等控制

## Capabilities

### New Capabilities

- `screen-selection`: 屏幕区域框选功能，包括全屏半透明覆盖层和可拖动的选区创建
- `ocr-recognition`: OCR 文字识别引擎，支持 PaddleOCR 和 Windows OCR API
- `change-monitor`: 定时监控循环，对比 OCR 结果并检测变化
- `plugin-system`: 插件加载器，支持按约定格式编写的 Python 插件文件
- `history-panel`: 历史记录显示面板，支持拖动、滚动、清空和导出

### Modified Capabilities

*None - this is a new application*

## Impact

- **新增依赖**: PyQt6/PySide6 (UI), PaddleOCR (OCR), Pillow (图像处理)
- **新增文件**: 完整的应用程序代码库
- **平台**: Windows 11 专属（依赖 Windows OCR API 和透明窗口特性）
- **打包**: 使用 PyInstaller 打包为独立可执行文件
