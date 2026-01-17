"""Abstract base class for virtualization backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from vcoding.core.types import ContainerState, WorkspaceConfig


class VirtualizationBackend(ABC):
    """Abstract base class for virtualization backends.

    This class defines the interface that all virtualization backends
    (Docker, Vagrant, etc.) must implement.
    """

    def __init__(self, config: WorkspaceConfig) -> None:
        """Initialize virtualization backend.

        Args:
            config: Workspace configuration.
        """
        self._config = config

    @property
    def config(self) -> WorkspaceConfig:
        """Get workspace configuration."""
        return self._config

    @abstractmethod
    def build(self, dockerfile_content: str | None = None) -> str:
        """Build the virtual environment image.

        Args:
            dockerfile_content: Optional Dockerfile content to use.
                If None, uses the Dockerfile from config.

        Returns:
            Image ID or name.
        """
        pass

    @abstractmethod
    def create(self, image: str | None = None) -> str:
        """Create a new virtual environment instance.

        Args:
            image: Optional image to use. If None, builds from config.

        Returns:
            Instance ID (container ID, VM ID, etc.).
        """
        pass

    @abstractmethod
    def start(self, instance_id: str) -> None:
        """Start a virtual environment instance.

        Args:
            instance_id: Instance ID to start.
        """
        pass

    @abstractmethod
    def stop(self, instance_id: str, timeout: int = 10) -> None:
        """Stop a virtual environment instance.

        Args:
            instance_id: Instance ID to stop.
            timeout: Timeout in seconds for graceful shutdown.
        """
        pass

    @abstractmethod
    def destroy(self, instance_id: str) -> None:
        """Destroy a virtual environment instance.

        Args:
            instance_id: Instance ID to destroy.
        """
        pass

    @abstractmethod
    def get_state(self, instance_id: str) -> ContainerState:
        """Get the state of a virtual environment instance.

        Args:
            instance_id: Instance ID to check.

        Returns:
            Current state of the instance.
        """
        pass

    @abstractmethod
    def execute(
        self,
        instance_id: str,
        command: str | list[str],
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command in the virtual environment.

        Args:
            instance_id: Instance ID.
            command: Command to execute.
            workdir: Working directory for the command.
            env: Environment variables.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        pass

    @abstractmethod
    def copy_to(
        self,
        instance_id: str,
        local_path: Path,
        remote_path: str,
    ) -> None:
        """Copy files to the virtual environment.

        Args:
            instance_id: Instance ID.
            local_path: Local file or directory path.
            remote_path: Remote destination path.
        """
        pass

    @abstractmethod
    def copy_from(
        self,
        instance_id: str,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """Copy files from the virtual environment.

        Args:
            instance_id: Instance ID.
            remote_path: Remote file or directory path.
            local_path: Local destination path.
        """
        pass

    @abstractmethod
    def get_ssh_config(self, instance_id: str) -> dict[str, Any]:
        """Get SSH connection configuration for the instance.

        Args:
            instance_id: Instance ID.

        Returns:
            Dictionary with SSH connection parameters.
        """
        pass

    @abstractmethod
    def get_logs(self, instance_id: str, tail: int | None = None) -> str:
        """Get logs from the virtual environment.

        Args:
            instance_id: Instance ID.
            tail: Number of lines to return from the end.

        Returns:
            Log output.
        """
        pass

    @abstractmethod
    def list_instances(self) -> list[dict[str, Any]]:
        """List all instances managed by this backend.

        Returns:
            List of instance information dictionaries.
        """
        pass
