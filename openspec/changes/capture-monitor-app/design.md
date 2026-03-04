# Design: CaptureMonitor Application

## Context

CaptureMonitor is a new Windows desktop application for monitoring screen regions and detecting text changes. The application needs to:

1. Display a full-screen overlay for region selection (independent from main window)
2. Perform OCR on selected regions at configurable intervals
3. Detect text changes and maintain a history log
4. Support an extensible plugin system for different monitoring scenarios
5. Run on Windows 11 with modern UI aesthetics

**Constraints:**
- Platform: Windows 11 only
- Language: Python
- Must support Chinese text recognition
- Simple file-based plugin system (.py files)
- Single-user desktop application (no multi-user concerns)

## Goals / Non-Goals

**Goals:**
- Create a functional OCR monitoring tool with the five core capabilities (screen selection, OCR recognition, change monitoring, plugin system, history panel)
- Support both PaddleOCR and Windows OCR API engines
- Implement a simple, file-convention-based plugin system
- Provide modern, Windows 11-style UI with independent, draggable windows
- Package as a standalone executable

**Non-Goals:**
- Cross-platform support (Windows 11 only)
- Cloud sync or remote monitoring
- Advanced plugin management (marketplace, auto-update, etc.)
- Database storage (in-memory history only)
- Multi-language UI (Chinese UI only)

## Decisions

### UI Framework: PyQt6

**Decision:** Use PyQt6 as the GUI framework.

**Rationale:**
- Best-looking UI on Windows 11 with native styling
- Excellent support for transparent/overlay windows (critical for screen selection)
- Mature drag-and-drop and window management APIs
- Large community and documentation

**Alternatives considered:**
- **Tkinter**: Too basic, limited transparency support, dated appearance
- **PySide6**: Equivalent to PyQt6, but PyQt6 has slightly better Windows 11 integration
- **Electron**: Would require JavaScript/TypeScript, overkill for this scope

### OCR Engine: Dual Support (PaddleOCR primary, Windows OCR fallback)

**Decision:** Support both PaddleOCR and Windows OCR API, defaulting to PaddleOCR.

**Rationale:**
- **PaddleOCR**: Best Chinese text recognition accuracy, actively maintained
- **Windows OCR API**: Zero-dependency fallback for users who don't want to install PaddleOCR
- User choice accommodates different preferences for accuracy vs. convenience

**Alternatives considered:**
- **Tesseract**: Older, inferior Chinese recognition
- **Cloud OCR APIs**: Would require internet, privacy concerns, cost

### Plugin System: File-Convention Based

**Decision:** Plugins are simple Python files in `./plugins/` that implement specific functions.

**Rationale:**
- Extreme simplicity: no manifests, registration, or complex APIs
- Easy for users to create and edit plugins
- No plugin marketplace or distribution complexity
- Restart required for changes (simplifies implementation)

**Contract:**
```python
def plugin_info() -> dict
def process_text(text: str) -> str
def format_change(old: str, new: str) -> str
```

**Alternatives considered:**
- **Class-based plugins**: More complex, unnecessary for this use case
- **Entry points**: Overkill, requires packaging
- **Hot-reload**: Adds complexity (import caching, state management)

### Window Architecture: Three Independent Windows

**Decision:** Three separate PyQt windows that operate independently:

1. **Main Control Window**: Settings, OCR selection, plugin selection, start/stop controls
2. **Overlay Window**: Full-screen semi-transparent window for region selection
3. **History Panel**: Independent draggable window for displaying results

**Rationale:**
- Overlay needs to be full-screen and work regardless of main window state
- History panel needs to be draggable and always visible
- Main window can be minimized without affecting monitoring
- Clean separation of concerns

**Alternatives considered:**
- **Single window with MDI**: Too restrictive, can't monitor other apps
- **Docked panels**: Less flexibility, Windows 11 users expect draggable windows

### Monitoring Loop: QTimer-Based

**Decision:** Use PyQt's QTimer for the monitoring loop.

**Rationale:**
- Native to Qt, integrates with event loop
- Simple start/stop API
- Non-blocking (runs in main thread but OCR is fast enough)

**Alternatives considered:**
- **threading.Timer**: More complex, requires thread safety
- **asyncio**: Overkill for this use case
- **Separate thread**: Adds complexity without significant benefit

### Directory Structure

```
capture-demo/
├── main.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # Main control window
│   ├── overlay_window.py   # Full-screen overlay
│   └── history_panel.py    # History display panel
├── core/
│   ├── __init__.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── base.py         # OCR base class
│   │   ├── paddle_ocr.py   # PaddleOCR implementation
│   │   └── windows_ocr.py  # Windows OCR implementation
│   ├── monitor.py          # Monitoring loop
│   └── plugin_loader.py    # Plugin discovery and loading
├── plugins/
│   ├── __init__.py
│   └── subtitle.py         # First plugin: subtitle monitoring
├── utils/
│   ├── __init__.py
│   └── screen_capture.py   # Screen region capture utility
├── requirements.txt
└── README.md
```

## Risks / Trade-offs

### Risk: PaddleOCR Installation Size

**Risk:** PaddleOCR + PaddlePaddle packages are large (~200MB+), affecting download/install time.

**Mitigation:**
- Make PaddleOCR optional (install as extra dependency)
- Provide clear instructions for Windows OCR as lightweight alternative
- Use PyInstaller's --onefile to create single executable

### Risk: Overlay Window Performance

**Risk:** Full-screen transparent window may impact system performance.

**Mitigation:**
- Use efficient Qt window attributes (FramelessWindowHint, WindowStaysOnTopHint)
- Minimize repaint frequency (only update when selection changes)
- Test on lower-end systems

### Risk: Plugin Errors Crash Application

**Risk:** Malformed or buggy plugins could crash the main application.

**Mitigation:**
- Wrap all plugin calls in try-except blocks
- Log errors and skip problematic plugins during discovery
- Return sensible defaults when plugin functions fail

### Trade-off: Restart Required for Plugin Changes

**Decision:** Users must restart the application to see plugin changes.

**Rationale:** Simplifies implementation (no hot-reload complexity).

**Mitigation:** Document clearly, plugin development is infrequent for end users.

### Trade-off: 1000 Entry History Limit

**Decision:** Maximum 1000 history entries, oldest removed when exceeded.

**Rationale:** Prevents unbounded memory growth.

**Mitigation:** Export functionality allows users to save important history.

## Migration Plan

This is a new application with no existing users. No migration needed.

### Deployment Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Run application: `python main.py`
3. For distribution: `pyinstaller --onefile --windowed main.py`

### Rollback Strategy

No server-side deployment. Rollback = uninstall and reinstall previous version.

## Open Questions

None - all design decisions are finalized for the first release.

### Future Considerations (Out of Scope)

- Tray icon for background operation
- Global hotkey for start/stop monitoring
- Multiple simultaneous monitoring regions
- Plugin configuration UI (currently hardcoded in plugin files)
- Sound notifications on change detection
- Dark mode theme
