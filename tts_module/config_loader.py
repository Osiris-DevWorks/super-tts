"""
Configuration Loader
Load and manage bot configuration from YAML
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration"""

    def __init__(self, config_path: Path = Path('config/config.yaml')):
        """
        Initialize configuration loader

        Args:
            config_path: Path to YAML config file
        """
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f'Config file not found: {self.config_path}')
            self.config = {}
            return

        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}

            logger.info(f'Loaded configuration from {self.config_path}')
        except Exception as e:
            logger.error(f'Failed to load configuration: {e}')
            self.config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key

        Args:
            key: Configuration key (e.g., 'tts.device')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> dict:
        """
        Get entire configuration section

        Args:
            section: Section name (e.g., 'tts')

        Returns:
            Section dictionary
        """
        return self.config.get(section, {})

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access"""
        return self.get(key)
