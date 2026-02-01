"""Workspace management with virtualization integration."""

import logging
from pathlib import Path
from typing import Any

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.agents.claudecode import ClaudeCodeAgent
from vcoding.agents.copilot import CopilotAgent
from vcoding.core.manager import WorkspaceManager
from vcoding.core.types import (
    ContainerState,
    TargetType,
    VirtualizationType,
    WorkspaceConfig,
)
from vcoding.ssh.client import SSHClient
from vcoding.ssh.keys import SSHKeyManager
from vcoding.virtualization.base import VirtualizationBackend
from vcoding.virtualization.docker import DockerBackend
from vcoding.workspace.git import GitManager

logger = logging.getLogger(__name__)


class Workspace:
    """High-level workspace management with integrated virtualization.

    This class provides a unified interface for managing a development
    workspace with virtual environment, SSH access, Git management,
    and code agents.
    """

    def __init__(
        self,
        target: Path,
        name: str | None = None,
        language: str | None = None,
        config: WorkspaceConfig | None = None,
    ) -> None:
        """Initialize workspace.

        Args:
            target: Path to the target file or directory.
            name: Optional workspace name.
            language: Optional programming language for Docker image.
            config: Optional workspace configuration.
        """
        self._target_path = Path(target).resolve()

        # Determine target type
        if self._target_path.is_file():
            self._target_type = TargetType.FILE
        else:
            self._target_type = TargetType.DIRECTORY

        if config:
            self._config = config
            self._name = name or config.name or self._target_path.name
            # Override language if provided
            if language and self._config.language is None:
                self._config.language = language
        else:
            self._name = name or self._target_path.name
            manager = WorkspaceManager.from_target(self._target_path, self._name)
            self._config = manager.config
            # Set language if provided
            if language:
                self._config.language = language

        self._manager = WorkspaceManager(self._config)
        self._backend: VirtualizationBackend | None = None
        self._ssh_client: SSHClient | None = None
        self._ssh_key_manager: SSHKeyManager | None = None
        self._git_manager: GitManager | None = None
        self._container_id: str | None = None
        self._agents: dict[str, CodeAgent] = {}

        # Set dockerfile_path to workspace temp dir (per SPEC.md 7.3)
        # so vcoding work files don't pollute user's project
        dockerfile_in_temp = self._manager.temp_dir / "Dockerfile"
        if dockerfile_in_temp.exists() and self._config.docker.dockerfile_path is None:
            self._config.docker.dockerfile_path = dockerfile_in_temp

    @property
    def name(self) -> str:
        """Get workspace name."""
        return self._name

    @property
    def target_path(self) -> Path:
        """Get target path."""
        return self._target_path

    @property
    def target_type(self) -> TargetType:
        """Get target type."""
        return self._target_type

    # Keep project_path for backward compatibility
    @property
    def project_path(self) -> Path:
        """Get project path (alias for target_path)."""
        return self._target_path

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
            # For file targets, use parent directory for git
            git_path = (
                self._target_path.parent
                if self._target_type == TargetType.FILE
                else self._target_path
            )
            self._git_manager = GitManager(git_path, self._config.git)
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

        Creates necessary directories in the vcoding app data folder.
        Does NOT modify the user's project directory (per SPEC.md 7.3).
        Git initialization happens inside the container (per SPEC.md 8.1).
        """
        self._manager.initialize()

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

        # Re-sync previously synced files
        self._resync_files()

        # Initialize Git inside container if configured (per SPEC.md 8.1)
        if self._config.git.auto_init:
            self._init_git_in_container()

        return self._container_id

    def _init_git_in_container(self) -> None:
        """Initialize Git repository inside the container."""
        if self._ssh_client is None:
            return

        work_dir = self._config.docker.work_dir

        # Check if .git already exists
        exit_code, _, _ = self._ssh_client.execute(
            f"test -d {work_dir}/.git", timeout=10
        )
        if exit_code == 0:
            # Already initialized
            return

        # Initialize git
        self._ssh_client.execute(f"cd {work_dir} && git init", timeout=30)

        # Configure git user (required for commits)
        self._ssh_client.execute(
            f'cd {work_dir} && git config user.email "vcoding@localhost"', timeout=10
        )
        self._ssh_client.execute(
            f'cd {work_dir} && git config user.name "vcoding"', timeout=10
        )

        # Create .gitignore if configured
        if self._config.git.auto_gitignore and self._config.git.default_gitignore:
            gitignore_content = "\\n".join(self._config.git.default_gitignore)
            self._ssh_client.execute(
                f'cd {work_dir} && echo -e "{gitignore_content}" > .gitignore',
                timeout=10,
            )

        # Initial commit if configured
        if self._config.git.auto_commit:
            self._ssh_client.execute(
                f"cd {work_dir} && git add -A && git commit -m 'Initial commit' --allow-empty",
                timeout=30,
            )

    def _resync_files(self) -> None:
        """Re-sync files that were previously synced."""
        synced_files = self._manager.get_synced_files()

        for entry in synced_files:
            source = Path(entry["source"])
            destination = entry["destination"]
            # Use flatten if this was the main sync (source is target_path)
            flatten = source == self._target_path

            if source.exists():
                try:
                    self.backend.copy_to(
                        self._container_id, source, destination, flatten=flatten
                    )
                    logger.debug(f"Re-synced: {source} -> {destination}")
                except Exception as e:
                    logger.warning(f"Failed to re-sync {source}: {e}")
            else:
                logger.warning(
                    f"Synced file no longer exists: {source}. "
                    f"Use prune_synced_files() to clean up."
                )

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

        # Clean up SSH keys
        self.ssh_key_manager.delete_key_pair(self._name)

        # Destroy workspace directory
        self._manager.destroy()

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

    def copy_to_container(
        self, local_path: Path, remote_path: str, record: bool = True
    ) -> None:
        """Copy files to the container.

        Args:
            local_path: Local file or directory.
            remote_path: Remote destination path.
            record: Whether to record this sync for auto-resync on restart.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_to(self._container_id, local_path, remote_path)

        # Record sync for auto-resync on restart
        if record:
            self._manager.add_synced_file(local_path, remote_path)

    def copy_from_container(self, remote_path: str, local_path: Path) -> None:
        """Copy files from the container.

        Args:
            remote_path: Remote file or directory.
            local_path: Local destination path.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        self.backend.copy_from(self._container_id, remote_path, local_path)

    def sync_to_container(self, record: bool = True) -> None:
        """Sync target files to the container.

        Args:
            record: Whether to record this sync for auto-resync on restart.
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        # Use flatten=True to copy directory contents directly to /workspace
        # instead of creating /workspace/project-name/
        self.backend.copy_to(
            self._container_id,
            self._target_path,
            self._config.docker.work_dir,
            flatten=True,
        )

        if record:
            self._manager.add_synced_file(
                self._target_path, self._config.docker.work_dir
            )

    def sync_from_container(
        self,
        target_path: Path | None = None,
        files: list[str] | None = None,
    ) -> None:
        """Sync files from the container to local.

        Per SPEC.md 7.3.6, only specified artifacts should be synced.

        Args:
            target_path: Local destination. Uses original target path if None.
            files: List of files to sync (relative to container work_dir).
                   If None, syncs entire work_dir (legacy behavior).
        """
        if self._container_id is None:
            raise RuntimeError("Workspace not started")

        destination = target_path or self._target_path
        if self._target_type == TargetType.FILE:
            destination = destination.parent

        if files:
            # Sync only specified files (per SPEC.md 7.3.6)
            for file_path in files:
                remote_path = f"{self._config.docker.work_dir}/{file_path}"
                local_path = destination / file_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                self.backend.copy_from(
                    self._container_id,
                    remote_path,
                    local_path.parent,
                    flatten=False,
                )
        else:
            # Legacy behavior: sync entire work_dir
            # Use flatten=True to extract /workspace contents directly
            self.backend.copy_from(
                self._container_id,
                self._config.docker.work_dir,
                destination,
                flatten=True,
            )

    def prune_synced_files(self) -> list[str]:
        """Remove records of non-existent synced files.

        Returns:
            List of removed source paths.
        """
        return self._manager.prune_synced_files()

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
        """Commit any pending changes inside the container.

        Args:
            message: Commit message.

        Returns:
            Commit hash if committed, None if no changes.
        """
        if self._ssh_client is None:
            raise RuntimeError("Workspace not started")

        work_dir = self._config.docker.work_dir
        msg = message or "Changes by vcoding"

        # Add all and commit
        exit_code, stdout, _ = self._ssh_client.execute(
            f'cd {work_dir} && git add -A && git diff --cached --quiet || git commit -m "{msg}"',
            timeout=30,
        )

        if exit_code == 0 and stdout.strip():
            # Get the commit hash
            _, hash_out, _ = self._ssh_client.execute(
                f"cd {work_dir} && git rev-parse HEAD",
                timeout=10,
            )
            return hash_out.strip() if hash_out else None
        return None

    def rollback_to(self, commit_ref: str, hard: bool = False) -> bool:
        """Rollback to a specific commit inside the container.

        Args:
            commit_ref: Commit hash or reference.
            hard: Whether to discard all changes.

        Returns:
            True if successful.
        """
        if self._ssh_client is None:
            raise RuntimeError("Workspace not started")

        work_dir = self._config.docker.work_dir
        reset_mode = "--hard" if hard else "--mixed"

        exit_code, _, _ = self._ssh_client.execute(
            f"cd {work_dir} && git reset {reset_mode} {commit_ref}",
            timeout=30,
        )
        return exit_code == 0

    def list_commits(self, max_count: int = 50) -> list[dict[str, str]]:
        """List recent commits inside the container.

        Args:
            max_count: Maximum number of commits.

        Returns:
            List of commit info dictionaries.
        """
        if self._ssh_client is None:
            raise RuntimeError("Workspace not started")

        work_dir = self._config.docker.work_dir

        exit_code, stdout, _ = self._ssh_client.execute(
            f'cd {work_dir} && git log --oneline -n {max_count} --format="%H|%s|%ai"',
            timeout=30,
        )

        if exit_code != 0 or not stdout.strip():
            return []

        commits = []
        for line in stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) >= 2:
                    commits.append(
                        {
                            "hash": parts[0],
                            "message": parts[1] if len(parts) > 1 else "",
                            "date": parts[2] if len(parts) > 2 else "",
                        }
                    )
        return commits

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

    def generate(
        self,
        prompt: str,
        output: str | None = None,
        agent: str = "copilot",
    ) -> AgentResult:
        """Generate code using a code agent (simplified API).

        This method hides container details - paths are relative to project.

        Args:
            prompt: What to generate (e.g., "Create a fibonacci function").
            output: Output file path relative to project (e.g., "fibonacci.py").
            agent: Agent to use ("copilot" or "claudecode").

        Returns:
            AgentResult with execution results.

        Example:
            ws.generate("Create a fibonacci function", output="fibonacci.py")
        """
        options = {}
        if output:
            # Convert relative path to container path
            container_path = f"{self._config.docker.work_dir}/{output}"
            options["output_file"] = container_path

        result = self.run_agent(agent, prompt, options=options)

        # Track generated file for selective sync (per SPEC.md 7.3.6)
        if output and result.success:
            if not hasattr(self, "_generated_files"):
                self._generated_files: list[str] = []
            self._generated_files.append(output)

        return result

    def run(
        self,
        command: str,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Run a command in the workspace (simplified API).

        Working directory is automatically set to the project root.

        Args:
            command: Command to execute.
            timeout: Optional timeout in seconds.

        Returns:
            Tuple of (exit_code, stdout, stderr).

        Example:
            exit_code, stdout, stderr = ws.run("python fibonacci.py")
        """
        return self.execute(
            command,
            workdir=self._config.docker.work_dir,
            timeout=timeout,
        )

    def __enter__(self) -> "Workspace":
        """Context manager entry."""
        self.start()
        self.sync_to_container()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if exc_type is None:
            # Only sync back if no exception occurred
            self.sync_from_container()
        self.stop()
