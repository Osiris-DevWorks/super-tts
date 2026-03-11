"""Tests for ConfigLoader"""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
import yaml
from utils.config_loader import ConfigLoader


class TestConfigLoaderGet:
    """Test ConfigLoader.get() dot-notation access"""

    def test_get_simple_key(self, tmp_path):
        """Test getting a simple top-level key"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        assert loader.get("tts.device") == "cuda"

    def test_get_nested_key(self, tmp_path):
        """Test getting nested key via dot notation"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  engine:\n    model: supertonic\n")

        loader = ConfigLoader(config_file)
        assert loader.get("tts.engine.model") == "supertonic"

    def test_get_with_default(self, tmp_path):
        """Test getting non-existent key returns default"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        result = loader.get("nonexistent.key", "default_value")
        assert result == "default_value"

    def test_get_missing_key_returns_none(self, tmp_path):
        """Test missing key without default returns None"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        result = loader.get("nonexistent")
        assert result is None

    def test_get_with_none_value_returns_default(self, tmp_path):
        """Test that None values return default"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  value: null\n")

        loader = ConfigLoader(config_file)
        result = loader.get("tts.value", "fallback")
        assert result == "fallback"

    def test_get_stops_at_non_dict(self, tmp_path):
        """Test that get stops traversing at non-dict value"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        # Trying to traverse beyond a string value
        result = loader.get("tts.device.model", "default")
        assert result == "default"

    def test_dictionary_style_access(self, tmp_path):
        """Test __getitem__ dictionary-style access"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        assert loader["tts.device"] == "cuda"


class TestConfigLoaderMissingFile:
    """Test ConfigLoader behavior with missing config file"""

    def test_loads_empty_dict_if_file_missing(self, tmp_path):
        """Test that missing file results in empty config"""
        config_file = tmp_path / "nonexistent.yaml"
        loader = ConfigLoader(config_file)
        assert loader.config == {}

    def test_get_returns_default_with_empty_config(self, tmp_path):
        """Test get with default on empty config"""
        config_file = tmp_path / "nonexistent.yaml"
        loader = ConfigLoader(config_file)
        result = loader.get("any.key", "default")
        assert result == "default"


class TestConfigLoaderGetSection:
    """Test ConfigLoader.get_section() method"""

    def test_get_section_returns_dict(self, tmp_path):
        """Test get_section returns entire section"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
tts:
  device: cuda
  model: supertonic
  voices: 10
""")
        loader = ConfigLoader(config_file)
        section = loader.get_section("tts")

        assert isinstance(section, dict)
        assert section["device"] == "cuda"
        assert section["model"] == "supertonic"
        assert section["voices"] == 10

    def test_get_section_missing_returns_empty(self, tmp_path):
        """Test missing section returns empty dict"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  device: cuda\n")

        loader = ConfigLoader(config_file)
        section = loader.get_section("nonexistent")
        assert section == {}


class TestConfigLoaderEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_yaml_file(self, tmp_path):
        """Test loading empty YAML file"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        loader = ConfigLoader(config_file)
        assert loader.config == {} or loader.config is None

    def test_list_values(self, tmp_path):
        """Test accessing list values"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("voices:\n  - male1\n  - female1\n")

        loader = ConfigLoader(config_file)
        voices = loader.get("voices")
        assert isinstance(voices, list)
        assert "male1" in voices

    def test_numeric_values(self, tmp_path):
        """Test numeric values in config"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  max_length: 500\n  speed: 1.5\n")

        loader = ConfigLoader(config_file)
        assert loader.get("tts.max_length") == 500
        assert loader.get("tts.speed") == 1.5

    def test_boolean_values(self, tmp_path):
        """Test boolean values in config"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("tts:\n  enabled: true\n  debug: false\n")

        loader = ConfigLoader(config_file)
        assert loader.get("tts.enabled") is True
        assert loader.get("tts.debug") is False
