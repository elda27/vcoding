"""Claude Code CLI agent."""

from typing import Any

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.ssh.client import SSHClient


class ClaudeCodeAgent(CodeAgent):
    """Anthropic Claude Code CLI agent."""

    def __init__(self, ssh_client: SSHClient) -> None:
        """Initialize Claude Code agent.

        Args:
            ssh_client: SSH client for remote execution.
        """
        super().__init__(ssh_client)

    @property
    def name(self) -> str:
        """Get agent name."""
        return "claude-code"

    @property
    def is_installed(self) -> bool:
        """Check if Claude Code CLI is installed."""
        return self._check_command_exists("claude")

    def execute(
        self,
        prompt: str,
        workdir: str | None = None,
        context_files: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute Claude Code with a prompt.

        Args:
            prompt: The prompt for Claude Code.
            workdir: Working directory.
            context_files: Files to provide as context.
            options: Additional options.
                - print: Print response to stdout (default: True)
                - output_format: Output format ("text", "json", "stream-json")
                - max_turns: Maximum conversation turns for agentic mode
                - model: Model to use (e.g., "claude-sonnet-4-20250514")
                - permission_mode: Permission mode ("default", "acceptEdits", "bypassPermissions")

        Returns:
            AgentResult with execution results.
        """
        options = options or {}

        # Create marker file for tracking modifications
        self._execute_command("touch /tmp/vcoding_marker", workdir=workdir)

        # Build command
        cmd_parts = ["claude"]

        # Add options
        if options.get("output_format"):
            cmd_parts.append(f"--output-format {options['output_format']}")

        if options.get("max_turns"):
            cmd_parts.append(f"--max-turns {options['max_turns']}")

        if options.get("model"):
            cmd_parts.append(f"--model {options['model']}")

        if options.get("permission_mode"):
            mode = options["permission_mode"]
            if mode == "acceptEdits":
                cmd_parts.append("--allowedTools Edit,Write,NotebookEdit")
            elif mode == "bypassPermissions":
                cmd_parts.append("--dangerously-skip-permissions")

        # Add print flag (default True)
        if options.get("print", True):
            cmd_parts.append("--print")

        # Add prompt (escaped)
        escaped_prompt = prompt.replace('"', '\\"')
        cmd_parts.append(f'"{escaped_prompt}"')

        command = " ".join(cmd_parts)

        # Execute
        exit_code, stdout, stderr = self._execute_command(
            command,
            workdir=workdir,
            timeout=options.get("timeout", 300),  # Default 5 min timeout
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
                "model": options.get("model"),
                "output_format": options.get("output_format"),
            },
        )

    def run_claude(
        self,
        prompt: str,
        workdir: str | None = None,
        print_output: bool = True,
    ) -> AgentResult:
        """Run a Claude Code prompt (convenience method).

        Args:
            prompt: Prompt to send to Claude.
            workdir: Working directory.
            print_output: Whether to print response to stdout.

        Returns:
            AgentResult with command results.
        """
        return self.execute(prompt, workdir=workdir, options={"print": print_output})

    def run_with_context(
        self,
        prompt: str,
        context_files: list[str],
        workdir: str | None = None,
    ) -> AgentResult:
        """Run Claude Code with specific context files.

        Args:
            prompt: Prompt to send to Claude.
            context_files: List of file paths to include as context.
            workdir: Working directory.

        Returns:
            AgentResult with command results.
        """
        # Claude Code automatically picks up files in the working directory
        # For specific files, we can cat them into the prompt
        if context_files:
            context_cmd = " && ".join([f"cat {f}" for f in context_files])
            full_prompt = f"Context from files:\n$({context_cmd})\n\nTask: {prompt}"
        else:
            full_prompt = prompt

        return self.execute(full_prompt, workdir=workdir)
