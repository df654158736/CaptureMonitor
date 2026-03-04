# CaptureMonitor

A Windows desktop tool for monitoring screen regions and detecting text changes.

## Features

- **Screen Region Selection**: Drag to select any area of your screen with a full-screen overlay
- **OCR Text Recognition**: Support for both PaddleOCR and Windows OCR API
- **Change Detection**: Automatically detects when text changes in the monitored region
- **History Panel**: View up to 1000 history entries with export functionality
- **Plugin System**: Extensible plugin architecture for custom text processing
- **Independent Windows**: Main control window, overlay, and history panel operate independently

## Requirements

- Windows 11
- Python 3.8+

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Click "Show Monitor Frame" to display the overlay
3. Drag on the overlay to select the region to monitor
4. Select an OCR engine and plugin
5. Set the monitoring interval (default: 2 seconds)
6. Click "Start Monitoring"

## OCR Engines

### PaddleOCR (Recommended)
- Best Chinese text recognition accuracy
- Requires additional installation space (~200MB)

### Windows OCR
- Built into Windows 11
- Zero additional dependencies
- Good accuracy for English text

## Plugins

Plugins are Python files in the `./plugins/` directory that implement:

```python
def plugin_info() -> dict:
    return {"name": "Plugin Name", "description": "...", "version": "1.0.0"}

def process_text(text: str) -> str:
    # Process OCR text
    return processed_text

def format_change(old: str, new: str) -> str:
    # Format change for display
    return f"{old} -> {new}"
```

## Building Executable

To create a standalone executable:

```bash
pyinstaller --onefile --windowed main.py
```

## License

MIT License
