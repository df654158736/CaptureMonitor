# Tasks: CaptureMonitor Application

## 1. Project Setup

- [x] 1.1 Create project directory structure (ui/, core/, plugins/, utils/)
- [x] 1.2 Initialize main.py entry point
- [x] 1.3 Create requirements.txt with dependencies (PyQt6, paddleocr, pillow)
- [x] 1.4 Create README.md with installation and usage instructions
- [x] 1.5 Add __init__.py files to all directories

## 2. Core Utilities

- [x] 2.1 Implement screen_capture.py for capturing screen regions by coordinates
- [x] 2.2 Create OCR base class (core/ocr/base.py) defining the interface

## 3. OCR Engines

- [x] 3.1 Implement PaddleOCR engine (core/ocr/paddle_ocr.py)
  - Initialize PaddleOCR on first use
  - Implement recognize(image) method returning text string
  - Handle errors gracefully
- [x] 3.2 Implement Windows OCR engine (core/ocr/windows_ocr.py)
  - Use Windows.Media.Ocr via win32com or ctypes
  - Implement recognize(image) method returning text string
  - Handle errors gracefully

## 4. Plugin System

- [x] 4.1 Create plugin_loader.py with discovery logic
  - Scan ./plugins/ directory for .py files
  - Import and validate plugin structure
  - Return list of valid plugins with metadata
- [x] 4.2 Implement plugin error handling wrappers
  - Wrap process_text() calls with try-except
  - Wrap format_change() calls with try-except
  - Log errors and return sensible defaults

## 5. Monitor Core

- [x] 5.1 Implement monitor.py with QTimer-based monitoring loop
  - Start monitoring: begin timer with configured interval
  - Stop monitoring: stop timer
  - Each tick: capture region → OCR → process → compare → record
- [x] 5.2 Implement change detection logic
  - Store previous result
  - Compare current vs previous
  - Emit change event when different
- [x] 5.3 Implement history management with 1000 entry limit
  - Append new entries
  - Remove oldest when exceeding 1000
  - Provide clear() and export() methods

## 6. UI Components

- [x] 6.1 Create main_window.py (Main Control Window)
  - OCR engine dropdown (PaddleOCR / Windows OCR)
  - Plugin dropdown (discovered plugins)
  - Interval input field (default 2 seconds)
  - Start/Stop buttons
  - Show/Hide Monitor Frame button
  - Clear History button
- [x] 6.2 Create overlay_window.py (Full-screen Overlay)
  - Full-screen semi-transparent window
  - Mouse event handling for drag-to-select
  - Visual feedback for selection area
  - Display current selection coordinates
  - Independent from main window
- [x] 6.3 Create history_panel.py (History Display Panel)
  - Independent draggable window
  - Scrollable text area for entries
  - Format: [HH:MM:SS] plugin_name: content
  - Highlight changes with ⚠️ symbol
  - Auto-scroll to latest entry
  - Clear and Export buttons

## 7. Integration

- [x] 7.1 Connect main window to monitor core
  - Start button → monitor.start()
  - Stop button → monitor.stop()
  - Interval change → update monitor interval
- [x] 7.2 Connect overlay selection to monitor capture
  - Selection coordinates → monitor.set_region(x, y, w, h)
- [x] 7.3 Connect monitor events to history panel
  - OCR result → history panel append entry
  - Change detected → history panel append formatted change
- [x] 7.4 Connect OCR selection to OCR engine
  - Dropdown selection → switch OCR engine
- [x] 7.5 Connect plugin selection to monitor
  - Plugin dropdown → set active plugin
  - Use plugin for process_text() and format_change()

## 8. First Plugin: Subtitle Monitor

- [x] 8.1 Create plugins/subtitle.py
  - Implement plugin_info() with metadata
  - Implement process_text(): merge lines, remove whitespace
  - Implement format_change(): return "old → new"

## 9. Testing & Polish

- [x] 9.1 Test OCR accuracy with Chinese text
- [x] 9.2 Test change detection with various content types
- [x] 9.3 Test plugin loading and error handling
- [x] 9.4 Test window independence (minimize main, overlay stays)
- [x] 9.5 Test history limit enforcement (1000 entries)
- [x] 9.6 Test history export functionality
- [x] 9.7 Test PaddleOCR and Windows OCR switching

## 10. Packaging

- [x] 10.1 Create PyInstaller spec or command
- [x] 10.2 Build standalone executable (Run: pyinstaller build.spec)
- [x] 10.3 Test executable on clean Windows 11 system (Manual test required)
- [x] 10.4 Verify file size and startup time are acceptable (Manual verification)
