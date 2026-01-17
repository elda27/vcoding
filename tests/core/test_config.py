"""Tests for vcoding.core.config module."""

import json
from pathlib import Path

import pytest

from vcoding.core.config import Config
from vcoding.core.types import VirtualizationType


class TestConfig:
    """Tests for Config class."""

    def test_init_without_path(self) -> None:
        """Test initialization without config path."""
        config = Config()
        assert config._config_path is None
        assert config._config_data == {}

    def test_init_with_path(self, temp_dir: Path) -> None:
        """Test initialization with config path."""
        config_path = temp_dir / "config.json"
        config = Config(config_path)
        assert config._config_path == config_path

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {"key": "value", "nested": {"inner": 123}}
        config = Config.from_dict(data)
        assert config.data == data

    def test_from_file(self, temp_dir: Path) -> None:
        """Test loading config from file."""
        config_path = temp_dir / "config.json"
        config_data = {"name": "test", "value": 42}
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        config = Config.from_file(config_path)
        assert config.get("name") == "test"
        assert config.get("value") == 42

    def test_load_nonexistent_file(self, temp_dir: Path) -> None:
        """Test loading from nonexistent file."""
        config_path = temp_dir / "nonexistent.json"
        config = Config(config_path)
        config.load()  # Should not raise
        assert config._config_data == {}

    def test_save(self, temp_dir: Path) -> None:
        """Test saving configuration."""
        config_path = temp_dir / "output.json"
        config = Config(config_path)
        config.set("test_key", "test_value")
        config.save()

        assert config_path.exists()
        loaded_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert loaded_data["test_key"] == "test_value"

    def test_save_to_different_path(self, temp_dir: Path) -> None:
        """Test saving to a different path."""
        config = Config()
        config.set("key", "value")

        output_path = temp_dir / "different.json"
        config.save(output_path)

        assert output_path.exists()

    def test_save_without_path_raises(self) -> None:
        """Test that saving without path raises error."""
        config = Config()
        with pytest.raises(ValueError, match="No path specified"):
            config.save()

    def test_get_simple_key(self) -> None:
        """Test getting simple key."""
        config = Config.from_dict({"key": "value"})
        assert config.get("key") == "value"

    def test_get_nested_key(self) -> None:
        """Test getting nested key with dot notation."""
        config = Config.from_dict({"level1": {"level2": {"level3": "deep_value"}}})
        assert config.get("level1.level2.level3") == "deep_value"

    def test_get_default_value(self) -> None:
        """Test getting default value for missing key."""
        config = Config()
        assert config.get("missing") is None
        assert config.get("missing", "default") == "default"

    def test_set_simple_key(self) -> None:
        """Test setting simple key."""
        config = Config()
        config.set("key", "value")
        assert config.get("key") == "value"

    def test_set_nested_key(self) -> None:
        """Test setting nested key with dot notation."""
        config = Config()
        config.set("a.b.c", "nested_value")
        assert config.get("a.b.c") == "nested_value"
        assert config.data["a"]["b"]["c"] == "nested_value"

    def test_to_workspace_config(self, temp_dir: Path) -> None:
        """Test converting to WorkspaceConfig."""
        config = Config.from_dict(
            {
                "virtualization_type": "docker",
                "docker": {
                    "base_image": "python:3.12",
                    "container_name_prefix": "test",
                },
                "ssh": {
                    "port": 2222,
                },
                "git": {
                    "auto_init": False,
                },
            }
        )

        workspace_config = config.to_workspace_config("test-ws", temp_dir)

        assert workspace_config.name == "test-ws"
        assert workspace_config.host_project_path == temp_dir
        assert workspace_config.virtualization_type == VirtualizationType.DOCKER
        assert workspace_config.docker.base_image == "python:3.12"
        assert workspace_config.docker.container_name_prefix == "test"
        assert workspace_config.ssh.port == 2222
        assert workspace_config.git.auto_init is False

    def test_data_property(self) -> None:
        """Test data property returns raw data."""
        data = {"a": 1, "b": 2}
        config = Config.from_dict(data)
        assert config.data == data
