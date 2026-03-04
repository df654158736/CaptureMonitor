"""
Plugin loader for discovering and loading plugins.
"""

import os
import sys
import importlib.util
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class Plugin:
    """Represents a loaded plugin."""

    def __init__(self, module: Any, plugin_id: str):
        self.module = module
        self.id = plugin_id
        self._info = None

    @property
    def name(self) -> str:
        """Get plugin name from plugin_info()."""
        info = self._get_info()
        return info.get('name', self.id)

    @property
    def description(self) -> str:
        """Get plugin description from plugin_info()."""
        info = self._get_info()
        return info.get('description', '')

    @property
    def version(self) -> str:
        """Get plugin version from plugin_info()."""
        info = self._get_info()
        return info.get('version', '1.0.0')

    def _get_info(self) -> Dict[str, Any]:
        """Get plugin info, caching the result."""
        if self._info is None:
            try:
                if hasattr(self.module, 'plugin_info'):
                    self._info = self.module.plugin_info()
                else:
                    self._info = {}
            except Exception as e:
                logger.error(f"Error getting plugin info from {self.id}: {e}")
                self._info = {}
        return self._info

    def process_text(self, text: str) -> str:
        """
        Process text through the plugin.

        Args:
            text: Raw OCR text

        Returns:
            Processed text
        """
        try:
            if hasattr(self.module, 'process_text'):
                return self.module.process_text(text)
        except Exception as e:
            logger.error(f"Error in plugin {self.id} process_text: {e}")
        return text

    def format_change(self, old: str, new: str) -> str:
        """
        Format a change for display.

        Args:
            old: Previous text
            new: Current text

        Returns:
            Formatted change string
        """
        try:
            if hasattr(self.module, 'format_change'):
                return self.module.format_change(old, new)
        except Exception as e:
            logger.error(f"Error in plugin {self.id} format_change: {e}")
        return f"{old} \u2192 {new}"


def discover_plugins(plugins_dir: str = None) -> List[Plugin]:
    """
    Discover and load all plugins from the plugins directory.

    Args:
        plugins_dir: Path to plugins directory (default: ./plugins/)

    Returns:
        List of loaded Plugin objects
    """
    if plugins_dir is None:
        # Get the directory where this file is located
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins_dir = os.path.join(base_dir, 'plugins')

    plugins = []

    if not os.path.exists(plugins_dir):
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return plugins

    # Add plugins directory to path for imports
    if plugins_dir not in sys.path:
        sys.path.insert(0, plugins_dir)

    for filename in os.listdir(plugins_dir):
        if not filename.endswith('.py') or filename.startswith('_'):
            continue

        plugin_id = filename[:-3]  # Remove .py extension
        filepath = os.path.join(plugins_dir, filename)

        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_id, filepath)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Validate plugin has required functions
            has_info = hasattr(module, 'plugin_info')
            has_process = hasattr(module, 'process_text')
            has_format = hasattr(module, 'format_change')

            if not (has_info and has_process and has_format):
                missing = []
                if not has_info:
                    missing.append('plugin_info')
                if not has_process:
                    missing.append('process_text')
                if not has_format:
                    missing.append('format_change')
                logger.warning(f"Plugin {plugin_id} missing functions: {', '.join(missing)}")
                continue

            plugin = Plugin(module, plugin_id)
            plugins.append(plugin)
            logger.info(f"Loaded plugin: {plugin.name} ({plugin_id})")

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_id}: {e}")
            continue

    return plugins


def get_plugin_by_id(plugins: List[Plugin], plugin_id: str) -> Optional[Plugin]:
    """
    Get a plugin by its ID.

    Args:
        plugins: List of loaded plugins
        plugin_id: Plugin ID to find

    Returns:
        Plugin if found, None otherwise
    """
    for plugin in plugins:
        if plugin.id == plugin_id:
            return plugin
    return None
