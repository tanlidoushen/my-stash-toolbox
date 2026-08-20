"""Plugin base class for stash-webhook-scanner-repaired."""

import logging

logger = logging.getLogger(__name__)


class BasePlugin:
    """Base class for all scraper plugins.
    
    Subclasses must implement the `scrape` method.
    Plugin classes are auto-discovered from the plugins/ directory
    and instantiated once at first use.
    """
    
    def __init__(self, stash_client=None):
        self.stash_client = stash_client
    
    @property
    def name(self) -> str:
        """Human-readable plugin name (defaults to class name)."""
        return self.__class__.__name__
    
    async def scrape(self, japanese_code: str, scene_info: dict = None) -> dict:
        """Scrape additional metadata for a JAV scene.
        
        Args:
            japanese_code: Normalized JAV code (e.g. START-273).
            scene_info: Optional dict with current scene metadata from Stash.
        
        Returns:
            dict with optional keys:
            - `performers`: list of dicts, each with `{'name': str}`
            - `urls`: list of URL strings to merge into the scene
        """
        raise NotImplementedError
