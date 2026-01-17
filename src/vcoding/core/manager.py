"""Workspace and working directory management."""

from pathlib import Path
from typing import TYPE_CHECKING

from vcoding.core.config import Config
from vcoding.core.types import WorkspaceConfig

if TYPE_CHECKING:
    from vcoding.virtualization.base import VirtualizationBackend


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

    @classmethod
    def from_path(
        cls, project_path: Path, name: str | None = None
    ) -> "WorkspaceManager":
        """Create workspace manager from project path.

        Args:
            project_path: Path to project directory.
            name: Optional workspace name. Uses directory name if None.

        Returns:
            WorkspaceManager instance.
        """
        project_path = Path(project_path).resolve()
        workspace_name = name or project_path.name

        # Try to load existing configuration
        config_path = project_path / ".vcoding" / "vcoding.json"
        if config_path.exists():
            config = Config.from_file(config_path)
            workspace_config = config.to_workspace_config(workspace_name, project_path)
        else:
            workspace_config = WorkspaceConfig(
                name=workspace_name,
                host_project_path=project_path,
            )

        return cls(workspace_config)

    @property
    def config(self) -> WorkspaceConfig:
        """Get workspace configuration."""
        return self._config

    @property
    def vcoding_dir(self) -> Path:
        """Get vcoding working directory."""
        return self._config.host_project_path / ".vcoding"

    @property
    def keys_dir(self) -> Path:
        """Get SSH keys directory."""
        return self.vcoding_dir / "keys"

    @property
    def temp_dir(self) -> Path:
        """Get temporary directory."""
        return self.vcoding_dir / "temp"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        return self.vcoding_dir / "logs"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.vcoding_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore for vcoding directory
        gitignore_path = self.vcoding_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("keys/\ntemp/\nlogs/\n", encoding="utf-8")

    def initialize(self) -> None:
        """Initialize workspace."""
        if self._initialized:
            return

        self.ensure_directories()
        self._initialized = True

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        # Clean up temp directory contents
        if self.temp_dir.exists():
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil

                    shutil.rmtree(item)

    def save_config(self) -> None:
        """Save current configuration."""
        config_path = self.vcoding_dir / "vcoding.json"
        config = Config()
        config._config_data = {
            "name": self._config.name,
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
