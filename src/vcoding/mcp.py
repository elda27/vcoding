"""MCP server for vcoding using FastMCP v2.

This module provides an MCP (Model Context Protocol) server that exposes
vcoding functions as tools for LLM agents.

Usage:
    # Run with FastMCP CLI
    fastmcp run vcoding.mcp:mcp

    # Or run directly
    python -m vcoding.mcp
"""

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from vcoding import functions

# Create the MCP server
mcp = FastMCP("vcoding", description="Virtualized development environment orchestration")

# Track active workspaces by name/path for stateful operations
_workspaces: dict[str, functions.Workspace] = {}


def _get_or_create_workspace(
    target: str,
    name: str | None = None,
    language: str | None = None,
) -> functions.Workspace:
    """Get existing workspace or create a new one."""
    key = name or target
    if key not in _workspaces:
        ws = functions.create_workspace(target, name=name, language=language)
        _workspaces[key] = ws
    return _workspaces[key]


def _get_workspace(target: str, name: str | None = None) -> functions.Workspace:
    """Get existing workspace."""
    key = name or target
    if key not in _workspaces:
        raise ValueError(f"Workspace not found: {key}. Create it first with create_workspace.")
    return _workspaces[key]


# =============================================================================
# Workspace Lifecycle Tools
# =============================================================================


@mcp.tool
def create_workspace(
    target: str,
    name: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Create a new workspace for a target file or directory.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name for identification.
        language: Optional programming language (python, nodejs, go, etc.)
            for template generation.

    Returns:
        Workspace info including target path and status.
    """
    ws = _get_or_create_workspace(target, name=name, language=language)
    return {
        "target": str(ws.target),
        "name": ws.name,
        "workspace_dir": str(ws.manager.workspace_dir),
        "status": "created",
    }


@mcp.tool
def start_workspace(target: str, name: str | None = None) -> dict[str, Any]:
    """Start a workspace's virtual environment (container).

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.

    Returns:
        Workspace info with running status.
    """
    key = name or target
    if key not in _workspaces:
        ws = functions.start_workspace(target, name=name)
        _workspaces[key] = ws
    else:
        ws = _workspaces[key]
        ws.start()
    return {
        "target": str(ws.target),
        "name": ws.name,
        "status": "running",
    }


@mcp.tool
def stop_workspace(target: str, name: str | None = None) -> dict[str, str]:
    """Stop a workspace's virtual environment.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.

    Returns:
        Status message.
    """
    ws = _get_workspace(target, name)
    functions.stop_workspace(ws)
    return {"status": "stopped", "target": str(ws.target)}


@mcp.tool
def destroy_workspace(target: str, name: str | None = None) -> dict[str, str]:
    """Destroy a workspace and clean up all resources.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.

    Returns:
        Status message.
    """
    key = name or target
    ws = _get_workspace(target, name)
    functions.destroy_workspace(ws)
    del _workspaces[key]
    return {"status": "destroyed", "target": str(ws.target)}


# =============================================================================
# Command Execution Tools
# =============================================================================


@mcp.tool
def execute_command(
    target: str,
    command: str,
    name: str | None = None,
    workdir: str | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Execute a command in the workspace container.

    Args:
        target: Path to the target file or directory.
        command: Shell command to execute.
        name: Optional workspace name.
        workdir: Working directory inside container.
        timeout: Command timeout in seconds.

    Returns:
        Command result with exit_code, stdout, stderr.
    """
    ws = _get_workspace(target, name)
    exit_code, stdout, stderr = functions.execute_command(
        ws, command, workdir=workdir, timeout=timeout
    )
    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "success": exit_code == 0,
    }


@mcp.tool
def run_in_workspace(
    target: str,
    command: str,
    timeout: int | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Run a command in a workspace (one-shot, handles full lifecycle).

    This is a convenience function that creates the workspace if needed,
    starts it, syncs files, runs the command, and returns results.

    Args:
        target: Path to the project directory.
        command: Command to execute.
        timeout: Optional timeout in seconds.
        language: Optional language for template generation.

    Returns:
        Command result with exit_code, stdout, stderr.
    """
    exit_code, stdout, stderr = functions.run(
        target, command, timeout=timeout, language=language
    )
    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "success": exit_code == 0,
    }


# =============================================================================
# Code Agent Tools
# =============================================================================


@mcp.tool
def run_agent(
    target: str,
    agent_type: str,
    prompt: str,
    name: str | None = None,
    workdir: str | None = None,
) -> dict[str, Any]:
    """Run a code agent (Copilot/Claude Code) in the workspace.

    Args:
        target: Path to the target file or directory.
        agent_type: Type of agent ("copilot" or "claudecode").
        prompt: Prompt/instruction for the agent.
        name: Optional workspace name.
        workdir: Working directory inside container.

    Returns:
        Agent execution result.
    """
    ws = _get_workspace(target, name)
    result = functions.run_agent(ws, agent_type, prompt, workdir=workdir)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "exit_code": result.exit_code,
    }


@mcp.tool
def generate_code(
    target: str,
    prompt: str,
    agent: str = "copilot",
    language: str | None = None,
) -> dict[str, Any]:
    """Generate code using an AI agent (one-shot, handles full lifecycle).

    Args:
        target: Path to the output file (e.g., "./my-project/fibonacci.py").
        prompt: What to generate (e.g., "Create a fibonacci function").
        agent: Agent to use ("copilot" or "claudecode").
        language: Optional language for template generation.

    Returns:
        Generation result with success status and output.
    """
    result = functions.generate(target, prompt, agent=agent, language=language)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "target": target,
    }


# =============================================================================
# File Sync Tools
# =============================================================================


@mcp.tool
def sync_to_workspace(
    target: str,
    name: str | None = None,
    local_path: str | None = None,
) -> dict[str, str]:
    """Sync files from host to workspace container.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.
        local_path: Optional specific local path to sync. Uses target if None.

    Returns:
        Status message.
    """
    ws = _get_workspace(target, name)
    functions.sync_to_workspace(ws, local_path=local_path)
    return {"status": "synced", "direction": "to_container"}


@mcp.tool
def sync_from_workspace(
    target: str,
    name: str | None = None,
    local_path: str | None = None,
) -> dict[str, str]:
    """Sync files from workspace container to host.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.
        local_path: Optional local destination path.

    Returns:
        Status message.
    """
    ws = _get_workspace(target, name)
    functions.sync_from_workspace(ws, local_path=local_path)
    return {"status": "synced", "direction": "from_container"}


# =============================================================================
# Git Operations Tools
# =============================================================================


@mcp.tool
def commit_changes(
    target: str,
    message: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Commit changes in the workspace.

    Args:
        target: Path to the target file or directory.
        message: Optional commit message.
        name: Optional workspace name.

    Returns:
        Commit info with hash if committed.
    """
    ws = _get_workspace(target, name)
    commit_hash = functions.commit_changes(ws, message=message)
    return {
        "committed": commit_hash is not None,
        "hash": commit_hash,
    }


@mcp.tool
def rollback(
    target: str,
    commit_ref: str,
    name: str | None = None,
    hard: bool = False,
) -> dict[str, Any]:
    """Rollback workspace to a specific commit.

    Args:
        target: Path to the target file or directory.
        commit_ref: Commit hash or reference to rollback to.
        name: Optional workspace name.
        hard: Whether to discard all changes (hard reset).

    Returns:
        Rollback status.
    """
    ws = _get_workspace(target, name)
    success = functions.rollback(ws, commit_ref, hard=hard)
    return {"success": success, "commit_ref": commit_ref}


@mcp.tool
def get_commits(
    target: str,
    name: str | None = None,
    max_count: int = 50,
) -> list[dict[str, str]]:
    """Get recent commits in the workspace.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.
        max_count: Maximum number of commits to return.

    Returns:
        List of commit info with hash, message, date.
    """
    ws = _get_workspace(target, name)
    return functions.get_commits(ws, max_count=max_count)


# =============================================================================
# Template Generation Tools
# =============================================================================


@mcp.tool
def generate_templates(
    project_path: str,
    language: str,
    dockerfile: bool = True,
    gitignore: bool = True,
) -> dict[str, str]:
    """Generate project templates (Dockerfile, .gitignore).

    Args:
        project_path: Path to the project directory.
        language: Programming language (python, nodejs, go, etc.).
        dockerfile: Whether to generate Dockerfile.
        gitignore: Whether to generate .gitignore.

    Returns:
        Paths of generated files.
    """
    generated = functions.generate_templates(
        project_path, language, dockerfile=dockerfile, gitignore=gitignore
    )
    return {k: str(v) for k, v in generated.items()}


@mcp.tool
def extend_dockerfile(
    dockerfile_path: str,
    output_path: str | None = None,
    user: str = "vcoding",
    work_dir: str = "/workspace",
) -> dict[str, str]:
    """Extend an existing Dockerfile with vcoding requirements.

    Adds SSH server, working user, and other requirements for vcoding.

    Args:
        dockerfile_path: Path to the original Dockerfile.
        output_path: Output path. Overwrites original if None.
        user: Username to create in container.
        work_dir: Working directory in container.

    Returns:
        Path to the extended Dockerfile.
    """
    result_path = functions.extend_dockerfile(
        dockerfile_path, output_path=output_path, user=user, work_dir=work_dir
    )
    return {"dockerfile": str(result_path)}


# =============================================================================
# Workspace Management Tools
# =============================================================================


@mcp.tool
def list_workspaces() -> list[dict[str, Any]]:
    """List all vcoding workspaces.

    Returns:
        List of workspace information.
    """
    return functions.list_all_workspaces()


@mcp.tool
def find_orphaned_workspaces() -> list[str]:
    """Find workspaces whose target paths no longer exist.

    Returns:
        List of orphaned workspace directory paths.
    """
    return [str(p) for p in functions.find_orphaned()]


@mcp.tool
def cleanup_orphaned_workspaces() -> dict[str, int]:
    """Remove orphaned workspaces.

    Returns:
        Number of removed workspaces.
    """
    count = functions.cleanup_orphaned()
    return {"removed_count": count}


@mcp.tool
def get_vcoding_data_dir() -> dict[str, str]:
    """Get the vcoding application data directory.

    Returns:
        Path to the application data directory.
    """
    return {"path": str(functions.get_vcoding_data_dir())}


# =============================================================================
# Resources
# =============================================================================


@mcp.resource("vcoding://workspaces")
def active_workspaces_resource() -> dict[str, Any]:
    """Get information about currently active workspaces."""
    return {
        "active_workspaces": [
            {
                "key": key,
                "target": str(ws.target),
                "name": ws.name,
            }
            for key, ws in _workspaces.items()
        ],
        "count": len(_workspaces),
    }


@mcp.resource("vcoding://config")
def config_resource() -> dict[str, Any]:
    """Get vcoding configuration information."""
    return {
        "data_dir": str(functions.get_vcoding_data_dir()),
        "version": "0.1.0",
    }


# =============================================================================
# Entry point
# =============================================================================


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
