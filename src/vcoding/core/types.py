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


class SSHConfig(BaseModel):
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
    host_project_path: Path
    virtualization_type: VirtualizationType = VirtualizationType.DOCKER
    docker: DockerConfig = Field(default_factory=DockerConfig)
    ssh: SSHConfig = Field(default_factory=SSHConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    temp_dir: Path | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def set_temp_dir(self) -> "WorkspaceConfig":
        """Set default temp_dir if not provided."""
        if self.temp_dir is None:
            self.temp_dir = self.host_project_path / ".vcoding"
        return self
