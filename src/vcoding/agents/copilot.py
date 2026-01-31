"""GitHub Copilot CLI agent.

GitHub Copilot CLI is installed via npm as @github/copilot.
It provides an agentic coding experience in the terminal.
See: https://github.com/github/copilot-cli
"""

from typing import Any

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.ssh.client import SSHClient


class CopilotAgent(CodeAgent):
    """GitHub Copilot CLI agent using @github/copilot.

    This agent uses the official GitHub Copilot CLI which provides
    agentic capabilities for code generation, editing, and debugging.
    """

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
        return self._check_command_exists("copilot")

    def execute(
        self,
        prompt: str,
        workdir: str | None = None,
        context_files: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute Copilot CLI with a prompt.

        The Copilot CLI is an interactive agent. This method runs it
        with the prompt passed via stdin using the -p flag for non-interactive mode.

        Args:
            prompt: The prompt for Copilot.
            workdir: Working directory.
            context_files: Files to provide as context.
            options: Additional options.
                - model: Model to use (e.g., "claude-sonnet-4", "gpt-4o")
                - allow_all_tools: Whether to auto-approve all tools (default: True)

        Returns:
            AgentResult with execution results.
        """
        options = options or {}
        allow_all_tools = options.get("allow_all_tools", True)
        model = options.get("model")

        # Create marker file for tracking modifications
        self._execute_command("touch /tmp/vcoding_marker", workdir=workdir)

        # Build command
        # Use -p/--prompt for prompt and --allow-all-tools for auto-approval
        escaped_prompt = prompt.replace("'", "'\\''")
        command = "copilot"

        if allow_all_tools:
            command += " --allow-all-tools"

        if model:
            command += f" --model {model}"

        command += f" -p '{escaped_prompt}'"

        # Get auth environment variables from options or host
        env = options.get("env") or self._get_auth_env()

        # Execute
        exit_code, stdout, stderr = self._execute_command(
            command,
            workdir=workdir,
            env=env,
            timeout=300,  # Longer timeout for agentic tasks
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
                "prompt": prompt,
                "model": model,
                "allow_all_tools": allow_all_tools,
            },
        )

    def _get_auth_env(self) -> dict[str, str]:
        """Get GitHub authentication environment variables from host.

        Checks for tokens in environment or from gh CLI.

        Returns:
            Dictionary of environment variables.
        """
        import os
        import subprocess

        env = {}

        # Check for GitHub tokens in environment
        for token_name in ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"]:
            token = os.environ.get(token_name)
            if token:
                env[token_name] = token
                return env

        # Try to get token from gh CLI
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                env["GH_TOKEN"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return env
