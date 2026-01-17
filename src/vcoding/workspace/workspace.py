"""Workspace management with virtualization integration."""

from pathlib import Path
from typing import Any

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.agents.claudecode import ClaudeCodeAgent
from vcoding.agents.copilot import CopilotAgent
from vcoding.core.manager import WorkspaceManager
from vcoding.core.types import ContainerState, VirtualizationType, WorkspaceConfig
from vcoding.ssh.client import SSHClient
from vcoding.ssh.keys import SSHKeyManager
from vcoding.virtualization.base import VirtualizationBackend
from vcoding.virtualization.docker import DockerBackend
from vcoding.workspace.git import GitManager


class Workspace:
    """High-level workspace management with integrated virtualization.

    This class provides a unified interface for managing a development
    workspace with virtual environment, SSH access, Git management,
    and code agents.
    """

    def __init__(
        self,
        project_path: Path,
        name: str | None = None,
        config: WorkspaceConfig | None = None,
    ) -> None:
        """Initialize workspace.

        Args:
            project_path: Path to the project directory.
            name: Optional workspace name.
            config: Optional workspace configuration.
        """
        self._project_path = Path(project_path).resolve()

        if config:
            self._config = config
            self._name = name or config.name or self._project_path.name
        else:
            self._name = name or self._project_path.name
            manager = WorkspaceManager.from_path(self._project_path, self._name)
            self._config = manager.config

        self._manager = WorkspaceManager(self._config)
        self._backend: VirtualizationBackend | None = None
        self._ssh_client: SSHClient | None = None
        self._ssh_key_manager: SSHKeyManager | None = None
        self._git_manager: GitManager | None = None
        self._container_id: str | None = None
        self._agents: dict[str, CodeAgent] = {}

    @property
    def name(self) -> str:
        """Get workspace name."""
        return self._name

    @property
    def project_path(self) -> Path:
        """Get project path."""
        return self._project_path

    @property
    def config(self) -> WorkspaceConfig:
        """Get workspace configuration."""
        return self._config

    @property
    def manager(self) -> WorkspaceManager:
        """Get workspace manager."""
        return self._manager

    @property
    def backend(self) -> VirtualizationBackend:
        """Get virtualization backend."""
        if self._backend is None:
            self._backend = self._create_backend()
        return self._backend

    @property
    def ssh_key_manager(self) -> SSHKeyManager:
        """Get SSH key manager."""
        if self._ssh_key_manager is None:
            self._ssh_key_manager = SSHKeyManager(self._manager.keys_dir)
        return self._ssh_key_manager

    @property
    def git(self) -> GitManager:
        """Get Git manager."""
        if self._git_manager is None:
            self._git_manager = GitManager(self._project_path, self._config.git)
        return self._git_manager

    @property
    def ssh(self) -> SSHClient | None:
        """Get SSH client (only available when container is running)."""
        return self._ssh_client

    @property
    def container_id(self) -> str | None:
        """Get current container ID."""
        return self._container_id

    @property
    def is_running(self) -> bool:
        """Check if the virtual environment is running."""
        if self._container_id is None:
            return False
        state = self.backend.get_state(self._container_id)
        return state == ContainerState.RUNNING

    def _create_backend(self) -> VirtualizationBackend:
        """Create virtualization backend based on config."""
        if self._config.virtualization_type == VirtualizationType.DOCKER:
            return DockerBackend(self._config)
        else:
            raise ValueError(
                f"Unsupported virtualization type: {self._config.virtualization_type}"
            )

    def initialize(self) -> None:
        """Initialize the workspace.

        Creates necessary directories, initializes Git if needed,
        and prepares the environment.
        """
        self._manager.initialize()

        # Initialize Git if configured
        if self._config.git.auto_init and not self.git.is_initialized:
            self.git.init()

        # Save configuration
        self._manager.save_config()

    def start(self, build: bool = True) -> str:
        """Start the virtual environment.

        Args:
            build: Whether to build the image if not exists.

        Returns:
            Container ID.
        """
        self.initialize()

        # Generate SSH keys
        key_pair = self.ssh_key_manager.get_or_create_key_pair(self._name)

        # Create and start container
        if build:
            image_id = self.backend.build()
        else:
            image_id = None

        self._container_id = self.backend.create(image_id)
        self.backend.start(self._container_id)

        # Inject SSH key
        if isinstance(self.backend, DockerBackend):
            self.backend.inject_ssh_key(self._container_id, key_pair.public_key_content)

        # Wait for SSH and create client
        ssh_config = self.backend.get_ssh_config(self._container_id)
        self._ssh_client = SSHClient(
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            private_key_path=key_pair.private_key_path,
        )

        # Wait for connection
        if not self._ssh_client.wait_for_connection(max_retries=60, retry_interval=1.0):
            raise RuntimeError("Failed to establish SSH connection to container")

        return self._container_id

    def stop(self, timeout: int = 10) -> None:
        """Stop the virtual environment.

        Args:
            timeout: Timeout for graceful shutdown.
        """
        if self._container_id:
            self.backend.stop(self._container_id, timeout=timeout)
            self._ssh_client = None

    def destroy(self) -> None:
        """Destroy the virtual environment and clean up resources."""
        if self._container_id:
            self.backend.destroy(self._container_id)
            self._container_id = None
            self._ssh_client = None

        # Optionally clean up SSH keys
        self.ssh_key_manager.delete_key_pair(self._name)

    def execute(
        self,
        command: str,
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command in the virtual environment.

        Args:
            command: Command to execute.
            workdir: Working directory.
            env: Environment variables.
            timeout: Command timeout.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        if self._ssh_client is None:
            raise RuntimeError("Workspace not started")

        return self._ssh_client.execute(
            command,
            workdir=workdir or self._config.docker.work_dir,
            env=env,
            timeout=timeout,
        )

    def copy_to_container(self, local_path: Path, remote_path: str) -> None:
        """Copy files to the container.

        Args:
            local_path: Local file or directory.
            remote_path: Remote destination path.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_to(self._container_id, local_path, remote_path)

    def copy_from_container(self, remote_path: str, local_path: Path) -> None:
        """Copy files from the container.

        Args:
            remote_path: Remote file or directory.
            local_path: Local destination path.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_from(self._container_id, remote_path, local_path)

    def sync_to_container(self) -> None:
        """Sync project files to the container."""
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_to(
            self._container_id,
            self._project_path,
            self._config.docker.work_dir,
        )

    def sync_from_container(self, target_path: Path | None = None) -> None:
        """Sync files from the container to local.

        Args:
            target_path: Local destination. Uses project path if None.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_from(
            self._container_id,
            self._config.docker.work_dir,
            target_path or self._manager.temp_dir,
        )

    def get_agent(self, agent_type: str) -> CodeAgent:
        """Get a code agent.

        Args:
            agent_type: Type of agent ("copilot" or "claudecode").

        Returns:
            CodeAgent instance.
        """
        if self._ssh_client is None:
            raise RuntimeError("Workspace not started")

        if agent_type not in self._agents:
            if agent_type == "copilot":
                self._agents[agent_type] = CopilotAgent(self._ssh_client)
            elif agent_type == "claudecode":
                self._agents[agent_type] = ClaudeCodeAgent(self._ssh_client)
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")

        return self._agents[agent_type]

    def run_agent(
        self,
        agent_type: str,
        prompt: str,
        workdir: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Run a code agent.

        Args:
            agent_type: Type of agent.
            prompt: Prompt for the agent.
            workdir: Working directory.
            options: Agent-specific options.

        Returns:
            AgentResult.
        """
        agent = self.get_agent(agent_type)
        return agent.execute(
            prompt,
            workdir=workdir or self._config.docker.work_dir,
            options=options,
        )

    def commit_changes(self, message: str | None = None) -> str | None:
        """Commit any pending changes.

        Args:
            message: Commit message.

        Returns:
            Commit hash if committed, None if no changes.
        """
        return self.git.auto_commit_changes(message or "Changes by vcoding")

    def rollback_to(self, commit_ref: str, hard: bool = False) -> bool:
        """Rollback to a specific commit.

        Args:
            commit_ref: Commit hash or reference.
            hard: Whether to discard all changes.

        Returns:
            True if successful.
        """
        return self.git.rollback(commit_ref, hard=hard)

    def get_logs(self, tail: int | None = None) -> str:
        """Get container logs.

        Args:
            tail: Number of lines from end.

        Returns:
            Log output.
        """
        if self._container_id is None:
            return ""
        return self.backend.get_logs(self._container_id, tail=tail)

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self._manager.cleanup()

    def __enter__(self) -> "Workspace":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
