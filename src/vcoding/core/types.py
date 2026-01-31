"""Type definitions for vcoding."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT


class VirtualizationType(Enum):
    """Supported virtualization types."""

    DOCKER = "docker"
    VAGRANT = "vagrant"  # Future support


class ContainerState(Enum):
    """Container/VM state."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    NOT_FOUND = "not_found"
    ERROR = "error"


class TargetType(Enum):
    """Target type for workspace."""

    FILE = "file"
    DIRECTORY = "directory"


class SshConfig(BaseModel):
    """SSH connection configuration."""

    host: str = "localhost"
    port: int = 22
    username: str = "vcoding"
    private_key_path: Path | None = None
    timeout: int = 30

    model_config = {"extra": "forbid"}


class DockerConfig(BaseModel):
    """Docker-specific configuration."""

    base_image: str = VCODING_DOCKER_OS_DEFAULT
    dockerfile_path: Path | None = None
    container_name_prefix: str = "vcoding"
    ssh_port: int = 22
    work_dir: str = "/workspace"
    user: str = "vcoding"
    mount_gh_config: bool = True  # Mount host's GitHub CLI config for authentication

    model_config = {"extra": "forbid"}


class GitConfig(BaseModel):
    """Git configuration."""

    auto_init: bool = True
    auto_commit: bool = True
    default_gitignore: list[str] = Field(
        default_factory=lambda: [
            "__pycache__/",
            "*.pyc",
            ".venv/",
            "node_modules/",
            ".env",
            "*.log",
            ".DS_Store",
            "Thumbs.db",
        ]
    )

    model_config = {"extra": "forbid"}


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""

    name: str
    target_path: Path
    target_type: TargetType = TargetType.DIRECTORY
    virtualization_type: VirtualizationType = VirtualizationType.DOCKER
    language: str | None = None
    docker: DockerConfig = Field(default_factory=DockerConfig)
    ssh: SshConfig = Field(default_factory=SshConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    workspace_dir: Path | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def set_workspace_dir(self) -> "WorkspaceConfig":
        """Set workspace_dir based on target_path if not provided."""
        if self.workspace_dir is None:
            from vcoding.core.paths import get_workspace_dir

            self.workspace_dir = get_workspace_dir(self.target_path)
        return self

    @property
    def temp_dir(self) -> Path:
        """Get temporary directory."""
        if self.workspace_dir is None:
            from vcoding.core.paths import get_workspace_dir

            return get_workspace_dir(self.target_path) / "temp"
        return self.workspace_dir / "temp"

    @property
    def keys_dir(self) -> Path:
        """Get SSH keys directory."""
        if self.workspace_dir is None:
            from vcoding.core.paths import get_workspace_dir

            return get_workspace_dir(self.target_path) / "keys"
        return self.workspace_dir / "keys"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        if self.workspace_dir is None:
            from vcoding.core.paths import get_workspace_dir

            return get_workspace_dir(self.target_path) / "logs"
        return self.workspace_dir / "logs"
