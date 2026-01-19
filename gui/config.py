"""
Settings Manager with JSON persistence.
Handles all application configuration with save/load functionality.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# Default settings file location
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json"
)


@dataclass
class Settings:
    """Application settings with defaults."""
    
    # Download settings
    output_dir: str = "downloads"
    max_threads: int = 4  # Concurrent chapters
    max_image_threads: int = 4  # Concurrent images per chapter
    delay: float = 1.0
    
    # Conversion options
    convert_to_pdf: bool = False
    convert_to_cbz: bool = False
    delete_images_after_conversion: bool = False
    
    # UI settings
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 800
    window_x: int = -1  # -1 means center
    window_y: int = -1
    
    # Recent URLs (max 10)
    recent_urls: List[str] = field(default_factory=list)
    
    def add_recent_url(self, url: str):
        """Add URL to recent list, keeping max 10."""
        if url in self.recent_urls:
            self.recent_urls.remove(url)
        self.recent_urls.insert(0, url)
        self.recent_urls = self.recent_urls[:10]


class SettingsManager:
    """Singleton settings manager with JSON persistence."""
    
    _instance: Optional['SettingsManager'] = None
    _settings: Optional[Settings] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = cls._instance._load()
        return cls._instance
    
    @property
    def settings(self) -> Settings:
        """Get current settings."""
        return self._settings
    
    def _load(self) -> Settings:
        """Load settings from JSON file."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Create Settings with loaded data, using defaults for missing keys
                    return Settings(**{
                        k: v for k, v in data.items() 
                        if k in Settings.__dataclass_fields__
                    })
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading settings: {e}")
        return Settings()
    
    def save(self):
        """Save current settings to JSON file."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._settings), f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")
    
    def reset(self):
        """Reset settings to defaults."""
        self._settings = Settings()
        self.save()
    
    def get(self, key: str, default=None):
        """Get a setting value by key."""
        return getattr(self._settings, key, default)
    
    def set(self, key: str, value):
        """Set a setting value by key."""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)


# Global settings instance
def get_settings() -> Settings:
    """Get the global settings instance."""
    return SettingsManager().settings


def save_settings():
    """Save current settings to file."""
    SettingsManager().save()


def reset_settings():
    """Reset settings to defaults."""
    SettingsManager().reset()
