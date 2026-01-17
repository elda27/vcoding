"""LangChain integration for vcoding.

This module provides LangChain-compatible tools for vcoding operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vcoding.workspace.workspace import Workspace

try:
    from langchain.tools import BaseTool
    from pydantic import BaseModel, Field

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = None  # type: ignore
    BaseModel = None  # type: ignore
    Field = None  # type: ignore


def get_langchain_tools(workspace: "Workspace") -> list[Any]:
    """Get all LangChain tools for a workspace.

    Args:
        workspace: Workspace instance.

    Returns:
        List of LangChain tools.

    Raises:
        ImportError: If LangChain is not installed.
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "LangChain is not installed. Install it with: pip install langchain"
        )

    return [
        _create_execute_tool(workspace),
        _create_copilot_tool(workspace),
        _create_git_commit_tool(workspace),
        _create_git_rollback_tool(workspace),
    ]


def _create_execute_tool(workspace: "Workspace") -> Any:
    """Create execute command tool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    class ExecuteCommandInput(BaseModel):  # type: ignore
        """Input for execute command tool."""

        command: str = Field(
            description="The command to execute in the virtual environment"
        )
        workdir: str | None = Field(
            default=None, description="Working directory for the command"
        )

    class ExecuteCommandTool(BaseTool):  # type: ignore
        """LangChain tool for executing commands in vcoding workspace."""

        name: str = "vcoding_execute"
        description: str = (
            "Execute a shell command in the vcoding virtual environment. "
            "Use this to run code, install packages, or perform any shell operation "
            "in an isolated container environment."
        )
        args_schema: type = ExecuteCommandInput
        _workspace: Any = None

        def __init__(self, ws: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._workspace = ws

        def _run(self, command: str, workdir: str | None = None) -> str:
            if self._workspace is None:
                return "Error: Workspace not initialized"

            exit_code, stdout, stderr = self._workspace.execute(
                command, workdir=workdir
            )

            result = f"Exit code: {exit_code}\n"
            if stdout:
                result += f"Output:\n{stdout}\n"
            if stderr:
                result += f"Errors:\n{stderr}\n"

            return result

        async def _arun(self, command: str, workdir: str | None = None) -> str:
            return self._run(command, workdir)

    return ExecuteCommandTool(workspace)


def _create_copilot_tool(workspace: "Workspace") -> Any:
    """Create Copilot tool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    class CopilotInput(BaseModel):  # type: ignore
        """Input for Copilot tool."""

        prompt: str = Field(description="The prompt or question for GitHub Copilot CLI")
        mode: str = Field(default="suggest", description="Mode: 'suggest' or 'explain'")

    class CopilotTool(BaseTool):  # type: ignore
        """LangChain tool for GitHub Copilot CLI."""

        name: str = "vcoding_copilot"
        description: str = (
            "Use GitHub Copilot CLI to get command suggestions or explanations. "
            "Set mode to 'suggest' for command suggestions or 'explain' for explanations."
        )
        args_schema: type = CopilotInput
        _workspace: Any = None

        def __init__(self, ws: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._workspace = ws

        def _run(self, prompt: str, mode: str = "suggest") -> str:
            if self._workspace is None:
                return "Error: Workspace not initialized"

            result = self._workspace.run_agent(
                "copilot",
                prompt,
                options={"mode": mode},
            )

            if result.success:
                return result.stdout
            return f"Error: {result.stderr}"

        async def _arun(self, prompt: str, mode: str = "suggest") -> str:
            return self._run(prompt, mode)

    return CopilotTool(workspace)


def _create_git_commit_tool(workspace: "Workspace") -> Any:
    """Create Git commit tool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    class GitCommitInput(BaseModel):  # type: ignore
        """Input for Git commit tool."""

        message: str = Field(description="Commit message")

    class GitCommitTool(BaseTool):  # type: ignore
        """LangChain tool for Git commits."""

        name: str = "vcoding_git_commit"
        description: str = (
            "Commit changes in the vcoding workspace with Git. "
            "This will stage all changes and create a commit."
        )
        args_schema: type = GitCommitInput
        _workspace: Any = None

        def __init__(self, ws: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._workspace = ws

        def _run(self, message: str) -> str:
            if self._workspace is None:
                return "Error: Workspace not initialized"

            commit_hash = self._workspace.commit_changes(message)
            if commit_hash:
                return f"Successfully committed changes: {commit_hash[:7]}"
            return "No changes to commit"

        async def _arun(self, message: str) -> str:
            return self._run(message)

    return GitCommitTool(workspace)


def _create_git_rollback_tool(workspace: "Workspace") -> Any:
    """Create Git rollback tool."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed")

    class GitRollbackInput(BaseModel):  # type: ignore
        """Input for Git rollback tool."""

        commit_ref: str = Field(description="Commit hash or reference to rollback to")
        hard: bool = Field(default=False, description="Whether to discard all changes")

    class GitRollbackTool(BaseTool):  # type: ignore
        """LangChain tool for Git rollback."""

        name: str = "vcoding_git_rollback"
        description: str = (
            "Rollback the vcoding workspace to a previous Git commit. "
            "Use hard=True to discard all changes."
        )
        args_schema: type = GitRollbackInput
        _workspace: Any = None

        def __init__(self, ws: Any, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._workspace = ws

        def _run(self, commit_ref: str, hard: bool = False) -> str:
            if self._workspace is None:
                return "Error: Workspace not initialized"

            success = self._workspace.rollback_to(commit_ref, hard=hard)
            if success:
                return f"Successfully rolled back to {commit_ref}"
            return f"Failed to rollback to {commit_ref}"

        async def _arun(self, commit_ref: str, hard: bool = False) -> str:
            return self._run(commit_ref, hard)

    return GitRollbackTool(workspace)
