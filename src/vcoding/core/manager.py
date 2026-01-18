"""Workspace and working directory management."""

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from vcoding.core.config import Config
from vcoding.core.paths import WorkspaceMetadata, get_workspace_dir
from vcoding.core.types import TargetType, WorkspaceConfig

if TYPE_CHECKING:
    from vcoding.virtualization.base import VirtualizationBackend

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspace and working directory lifecycle."""

    def __init__(self, config: WorkspaceConfig) -> None:
        """Initialize workspace manager.

        Args:
            config: Workspace configuration.
        """
        self._config = config
        self._backend: "VirtualizationBackend | None" = None
        self._initialized = False
        self._metadata: WorkspaceMetadata | None = None

    @classmethod
    def from_target(
        cls, target_path: Path, name: str | None = None
    ) -> "WorkspaceManager":
        """Create workspace manager from target path.

        Args:
            target_path: Path to target file or directory.
            name: Optional workspace name. Uses target name if None.

        Returns:
            WorkspaceManager instance.
        """
        target_path = Path(target_path).resolve()
        workspace_name = name or target_path.name
        workspace_dir = get_workspace_dir(target_path)

        # Determine target type
        if target_path.is_file():
            target_type = TargetType.FILE
        else:
            target_type = TargetType.DIRECTORY

        # Try to load existing configuration
        config_path = workspace_dir / "config.json"
        if config_path.exists():
            config = Config.from_file(config_path)
            workspace_config = config.to_workspace_config(workspace_name, target_path)
        else:
            workspace_config = WorkspaceConfig(
                name=workspace_name,
                target_path=target_path,
                target_type=target_type,
                workspace_dir=workspace_dir,
            )

        return cls(workspace_config)

    # Keep old method for backward compatibility
    @classmethod
    def from_path(
        cls, project_path: Path, name: str | None = None
    ) -> "WorkspaceManager":
        """Create workspace manager from project path (deprecated).

        Use from_target() instead.

        Args:
            project_path: Path to project directory.
            name: Optional workspace name.

        Returns:
            WorkspaceManager instance.
        """
        return cls.from_target(project_path, name)

    @property
    def config(self) -> WorkspaceConfig:
        """Get workspace configuration."""
        return self._config

    @property
    def workspace_dir(self) -> Path:
        """Get workspace directory in app data."""
        if self._config.workspace_dir:
            return self._config.workspace_dir
        return get_workspace_dir(self._config.target_path)

    @property
    def keys_dir(self) -> Path:
        """Get SSH keys directory."""
        return self.workspace_dir / "keys"

    @property
    def temp_dir(self) -> Path:
        """Get temporary directory."""
        return self.workspace_dir / "temp"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        return self.workspace_dir / "logs"

    @property
    def metadata(self) -> WorkspaceMetadata:
        """Get workspace metadata."""
        if self._metadata is None:
            self._metadata = WorkspaceMetadata(self.workspace_dir)
        return self._metadata

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Initialize workspace."""
        if self._initialized:
            return

        self.ensure_directories()

        # Initialize or update metadata
        if not self.metadata.exists():
            self.metadata.initialize(self._config.target_path)
        else:
            self.metadata.update_last_accessed()

        self._initialized = True

    def get_synced_files(self) -> list[dict[str, str]]:
        """Get list of synced files.

        Returns:
            List of synced file records.
        """
        return self.metadata.synced_files

    def add_synced_file(self, source: Path, destination: str) -> None:
        """Record a synced file.

        Args:
            source: Source path on host.
            destination: Destination path in container.
        """
        self.metadata.add_synced_file(source, destination)

    def prune_synced_files(self) -> list[str]:
        """Remove records of non-existent synced files.

        Returns:
            List of removed source paths.
        """
        removed = self.metadata.prune_synced_files()
        for path in removed:
            logger.info(f"Pruned non-existent synced file: {path}")
        return removed

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        # Clean up temp directory contents
        if self.temp_dir.exists():
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

    def destroy(self) -> None:
        """Destroy the workspace directory completely."""
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir, ignore_errors=True)

            # Clean up empty parent directory (hash prefix dir)
            parent = self.workspace_dir.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()

    def save_config(self) -> None:
        """Save current configuration."""
        config_path = self.workspace_dir / "config.json"
        config = Config()
        config._config_data = {
            "name": self._config.name,
            "target_path": str(self._config.target_path),
            "target_type": self._config.target_type.value,
            "virtualization_type": self._config.virtualization_type.value,
            "docker": {
                "base_image": self._config.docker.base_image,
                "dockerfile_path": (
                    str(self._config.docker.dockerfile_path)
                    if self._config.docker.dockerfile_path
                    else None
                ),
                "container_name_prefix": self._config.docker.container_name_prefix,
                "ssh_port": self._config.docker.ssh_port,
                "work_dir": self._config.docker.work_dir,
                "user": self._config.docker.user,
            },
            "ssh": {
                "host": self._config.ssh.host,
                "port": self._config.ssh.port,
                "username": self._config.ssh.username,
                "timeout": self._config.ssh.timeout,
            },
            "git": {
                "auto_init": self._config.git.auto_init,
                "auto_commit": self._config.git.auto_commit,
                "default_gitignore": self._config.git.default_gitignore,
            },
        }
        config.save(config_path)
