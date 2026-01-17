"""Configuration management for vcoding."""

import json
from pathlib import Path
from typing import Any

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT
from vcoding.core.types import (
    DockerConfig,
    GitConfig,
    SSHConfig,
    VirtualizationType,
    WorkspaceConfig,
)

DEFAULT_CONFIG_FILENAME = "vcoding.json"


class Config:
    """Configuration manager for vcoding."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        self._config_path = config_path
        self._config_data: dict[str, Any] = {}

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from file.

        Args:
            config_path: Path to configuration file.

        Returns:
            Config instance with loaded configuration.
        """
        instance = cls(config_path)
        instance.load()
        return instance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            Config instance.
        """
        instance = cls()
        instance._config_data = data
        return instance

    def load(self) -> None:
        """Load configuration from file."""
        if self._config_path is None or not self._config_path.exists():
            return

        with open(self._config_path, encoding="utf-8") as f:
            self._config_data = json.load(f)

    def save(self, path: Path | None = None) -> None:
        """Save configuration to file.

        Args:
            path: Path to save configuration. Uses config_path if None.
        """
        save_path = path or self._config_path
        if save_path is None:
            raise ValueError("No path specified for saving configuration")

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._config_data, f, indent=2, default=str)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key (supports dot notation).
            default: Default value if key not found.

        Returns:
            Configuration value.
        """
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key (supports dot notation).
            value: Value to set.
        """
        keys = key.split(".")
        data = self._config_data
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value

    def to_workspace_config(self, name: str, project_path: Path) -> WorkspaceConfig:
        """Convert configuration to WorkspaceConfig.

        Args:
            name: Workspace name.
            project_path: Path to project directory.

        Returns:
            WorkspaceConfig instance.
        """
        virt_type_str = self.get("virtualization_type", "docker")
        virt_type = VirtualizationType(virt_type_str)

        docker_data = self.get("docker", {})
        docker_config = DockerConfig(
            base_image=docker_data.get("base_image", VCODING_DOCKER_OS_DEFAULT),
            dockerfile_path=(
                Path(docker_data["dockerfile_path"])
                if docker_data.get("dockerfile_path")
                else None
            ),
            container_name_prefix=docker_data.get("container_name_prefix", "vcoding"),
            ssh_port=docker_data.get("ssh_port", 22),
            work_dir=docker_data.get("work_dir", "/workspace"),
            user=docker_data.get("user", "vcoding"),
        )

        ssh_data = self.get("ssh", {})
        ssh_config = SSHConfig(
            host=ssh_data.get("host", "localhost"),
            port=ssh_data.get("port", 22),
            username=ssh_data.get("username", "vcoding"),
            timeout=ssh_data.get("timeout", 30),
        )

        git_data = self.get("git", {})
        git_config = GitConfig(
            auto_init=git_data.get("auto_init", True),
            auto_commit=git_data.get("auto_commit", True),
            default_gitignore=git_data.get(
                "default_gitignore", GitConfig().default_gitignore
            ),
        )

        return WorkspaceConfig(
            name=name,
            host_project_path=project_path,
            virtualization_type=virt_type,
            docker=docker_config,
            ssh=ssh_config,
            git=git_config,
            temp_dir=Path(self.get("temp_dir")) if self.get("temp_dir") else None,
        )

    @property
    def data(self) -> dict[str, Any]:
        """Get raw configuration data."""
        return self._config_data
