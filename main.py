"""
Main entry point for the CaptureMonitor application.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from ui.overlay_window import OverlayWindow
from ui.history_panel import HistoryPanel
from ui.region_indicator import RegionIndicator
from core.monitor import Monitor
from core.plugin_loader import discover_plugins


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting CaptureMonitor...")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("CaptureMonitor")
    app.setApplicationVersion("1.0.0")

    # Create monitor core
    monitor = Monitor()

    # Create UI windows
    main_window = MainWindow()
    overlay_window = OverlayWindow()
    history_panel = HistoryPanel()
    region_indicator = RegionIndicator()

    # Load plugins
    plugins = discover_plugins()
    main_window.set_plugins(plugins)

    if plugins:
        logger.info(f"Loaded {len(plugins)} plugins: {[p.name for p in plugins]}")
        # Set first plugin as default
        main_window.plugin_combo.setCurrentIndex(1)
    else:
        logger.info("No plugins found")

    # Connect main window signals
    main_window.show_overlay_requested.connect(overlay_window.show)
    main_window.hide_overlay_requested.connect(overlay_window.hide)
    main_window.start_monitoring_requested.connect(monitor.start)
    main_window.stop_monitoring_requested.connect(monitor.stop)
    main_window.stop_monitoring_requested.connect(region_indicator.hide_indicator)
    main_window.clear_history_requested.connect(monitor.clear_history)
    main_window.clear_history_requested.connect(history_panel.clear)
    main_window.ocr_changed.connect(monitor.set_ocr_engine)
    main_window.plugin_changed.connect(monitor.set_plugin)
    main_window.interval_changed.connect(monitor.set_interval)

    # Connect overlay signals
    overlay_window.region_selected.connect(monitor.set_region)
    overlay_window.region_selected.connect(region_indicator.set_region)
    overlay_window.region_selected.connect(region_indicator.show_indicator)
    overlay_window.region_selected.connect(
        lambda x, y, w, h: main_window.update_status(f"\u5df2\u9009\u62e9\u533a\u57df: ({x}, {y}) {w}x{h}")
    )

    # Connect monitor signals
    monitor.text_detected.connect(lambda text: logger.debug(f"Detected: {text}"))
    monitor.change_detected.connect(
        lambda old, new: logger.info(f"Change: {old} -> {new}")
    )
    monitor.history_updated.connect(
        lambda: history_panel.set_history(monitor.get_history())
    )
    monitor.error_occurred.connect(
        lambda msg: main_window.update_status(f"Error: {msg}", is_error=True)
    )

    # Connect history panel signals
    history_panel.clear_requested.connect(monitor.clear_history)

    # Show windows
    main_window.show()
    history_panel.show()

    logger.info("CaptureMonitor started successfully")

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
