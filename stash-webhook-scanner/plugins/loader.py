"""Plugin discovery and loading."""

import importlib.util
import inspect
import logging
import os
import sys

from plugins.base import BasePlugin

logger = logging.getLogger("plugin")


class PluginLoader:
    """Discovers and loads plugins from a directory.
    
    Looks for files matching ``*_plugin.py`` (excluding ``base.py`` /
    ``loader.py``), imports each as a module, and instantiates every
    ``BasePlugin`` subclass found.
    
    Results are cached so the filesystem is only scanned once.
    """
    
    def __init__(self, plugin_dir):
        self.plugin_dir = os.path.abspath(plugin_dir) if plugin_dir else None
        self._plugins = None
    
    def discover(self, stash_client=None):
        """Return all discovered plugins (cached after first call)."""
        if self._plugins is not None:
            if stash_client is not None:
                for p in self._plugins:
                    p.stash_client = stash_client
            return self._plugins
        
        self._plugins = []
        
        if not self.plugin_dir or not os.path.isdir(self.plugin_dir):
            logger.debug("Plugin directory not available: %s", self.plugin_dir)
            return self._plugins
        
        # Add to sys.path so we can import plugin modules by name
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)
        
        for fname in sorted(os.listdir(self.plugin_dir)):
            if not fname.endswith('_plugin.py') or fname in ('base.py', 'loader.py', '__init__.py'):
                continue
            
            module_name = fname[:-3]
            try:
                module = importlib.import_module(module_name)
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj is BasePlugin:
                        continue
                    if issubclass(obj, BasePlugin):
                        plugin = obj(stash_client=stash_client)
                        self._plugins.append(plugin)
                        logger.info("已加载插件: %s", plugin.name)
            except Exception as e:
                logger.error("Failed to load plugin %s: %s", fname, e)
        
        return self._plugins
