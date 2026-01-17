"""Abstract base class for code agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from vcoding.ssh.client import SSHClient


@dataclass
class AgentResult:
    """Result from a code agent execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class CodeAgent(ABC):
    """Abstract base class for code agents.

    Code agents are CLI tools that can generate, modify, or analyze code.
    Examples: GitHub Copilot CLI, Cloud Code, etc.
    """

    def __init__(self, ssh_client: SSHClient) -> None:
        """Initialize code agent.

        Args:
            ssh_client: SSH client for remote execution.
        """
        self._ssh_client = ssh_client

    @property
    def ssh_client(self) -> SSHClient:
        """Get SSH client."""
        return self._ssh_client

    @property
    @abstractmethod
    def name(self) -> str:
        """Get agent name."""
        pass

    @property
    @abstractmethod
    def is_installed(self) -> bool:
        """Check if agent is installed in the remote environment."""
        pass

    @abstractmethod
    def execute(
        self,
        prompt: str,
        workdir: str | None = None,
        context_files: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the agent with a prompt.

        Args:
            prompt: The prompt or instruction for the agent.
            workdir: Working directory for execution.
            context_files: Files to provide as context.
            options: Additional agent-specific options.

        Returns:
            AgentResult with execution results.
        """
        pass

    def _execute_command(
        self,
        command: str,
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command via SSH.

        Args:
            command: Command to execute.
            workdir: Working directory.
            env: Environment variables.
            timeout: Command timeout.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        return self._ssh_client.execute(
            command,
            workdir=workdir,
            env=env,
            timeout=timeout,
        )

    def _check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the remote environment.

        Args:
            command: Command name to check.

        Returns:
            True if command exists.
        """
        exit_code, _, _ = self._execute_command(f"which {command}")
        return exit_code == 0

    def get_modified_files(
        self,
        workdir: str,
        before_time: str,
    ) -> list[str]:
        """Get files modified after a certain time.

        Args:
            workdir: Working directory to scan.
            before_time: Timestamp to compare against.

        Returns:
            List of modified file paths.
        """
        exit_code, stdout, _ = self._execute_command(
            f"find {workdir} -type f -newer /tmp/vcoding_marker 2>/dev/null || true",
            workdir=workdir,
        )
        if exit_code == 0 and stdout:
            return [f.strip() for f in stdout.strip().split("\n") if f.strip()]
        return []
