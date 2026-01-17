"""GitHub Copilot CLI agent."""

from typing import Any

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.ssh.client import SSHClient


class CopilotAgent(CodeAgent):
    """GitHub Copilot CLI agent."""

    def __init__(self, ssh_client: SSHClient) -> None:
        """Initialize Copilot agent.

        Args:
            ssh_client: SSH client for remote execution.
        """
        super().__init__(ssh_client)

    @property
    def name(self) -> str:
        """Get agent name."""
        return "github-copilot-cli"

    @property
    def is_installed(self) -> bool:
        """Check if Copilot CLI is installed."""
        return self._check_command_exists("gh") and self._check_copilot_extension()

    def _check_copilot_extension(self) -> bool:
        """Check if GitHub Copilot extension is installed."""
        exit_code, stdout, _ = self._execute_command("gh extension list")
        if exit_code == 0:
            return "copilot" in stdout.lower()
        return False

    def execute(
        self,
        prompt: str,
        workdir: str | None = None,
        context_files: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute Copilot CLI with a prompt.

        Args:
            prompt: The prompt for Copilot.
            workdir: Working directory.
            context_files: Files to provide as context.
            options: Additional options.
                - mode: "suggest" or "explain" (default: "suggest")
                - target: "shell", "git", or "gh" (default: "shell")

        Returns:
            AgentResult with execution results.
        """
        options = options or {}
        mode = options.get("mode", "suggest")
        target = options.get("target", "shell")

        # Create marker file for tracking modifications
        self._execute_command("touch /tmp/vcoding_marker", workdir=workdir)

        # Build command
        escaped_prompt = prompt.replace('"', '\\"').replace("$", "\\$")

        if mode == "explain":
            command = f'gh copilot explain "{escaped_prompt}"'
        else:
            command = f'gh copilot suggest -t {target} "{escaped_prompt}"'

        # Execute
        exit_code, stdout, stderr = self._execute_command(
            command,
            workdir=workdir,
            timeout=120,
        )

        # Get modified files
        modified_files = []
        if workdir:
            modified_files = self.get_modified_files(workdir, "/tmp/vcoding_marker")

        return AgentResult(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            files_modified=modified_files,
            metadata={
                "mode": mode,
                "target": target,
                "prompt": prompt,
            },
        )

    def suggest_command(
        self,
        prompt: str,
        target: str = "shell",
        workdir: str | None = None,
    ) -> AgentResult:
        """Get a command suggestion from Copilot.

        Args:
            prompt: Description of what you want to do.
            target: Target type ("shell", "git", or "gh").
            workdir: Working directory.

        Returns:
            AgentResult with suggested command.
        """
        return self.execute(
            prompt,
            workdir=workdir,
            options={"mode": "suggest", "target": target},
        )

    def explain_command(
        self,
        command: str,
        workdir: str | None = None,
    ) -> AgentResult:
        """Get an explanation of a command from Copilot.

        Args:
            command: Command to explain.
            workdir: Working directory.

        Returns:
            AgentResult with explanation.
        """
        return self.execute(
            command,
            workdir=workdir,
            options={"mode": "explain"},
        )
