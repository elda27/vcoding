"""vcoding - Virtualized development environment orchestration tool.

This package provides tools for creating and managing secure,
reproducible development environments using containerization.
"""

from vcoding.core.config import Config
from vcoding.core.types import (
    ContainerState,
    DockerConfig,
    GitConfig,
    SshConfig,
    VirtualizationType,
    WorkspaceConfig,
)
from vcoding.functions import (
    cleanup_orphaned,
    commit_changes,
    create_workspace,
    destroy_workspace,
    execute_command,
    extend_dockerfile,
    find_orphaned,
    generate,
    generate_templates,
    get_commits,
    get_vcoding_data_dir,
    list_all_workspaces,
    rollback,
    run,
    run_agent,
    start_workspace,
    stop_workspace,
    sync_from_workspace,
    sync_to_workspace,
    workspace_context,
)
from vcoding.workspace.workspace import Workspace

__version__ = "0.1.0"

__all__ = [
    # Core types
    "Config",
    "ContainerState",
    "DockerConfig",
    "GitConfig",
    "SshConfig",
    "VirtualizationType",
    "Workspace",
    "WorkspaceConfig",
    # One-shot functions (simple API)
    "generate",
    "run",
    # Context manager
    "workspace_context",
    # Workspace lifecycle functions
    "create_workspace",
    "start_workspace",
    "stop_workspace",
    "destroy_workspace",
    # Workspace operations
    "commit_changes",
    "execute_command",
    "get_commits",
    "rollback",
    "run_agent",
    "sync_from_workspace",
    "sync_to_workspace",
    # Template functions
    "extend_dockerfile",
    "generate_templates",
    # Workspace management utilities
    "cleanup_orphaned",
    "find_orphaned",
    "get_vcoding_data_dir",
    "list_all_workspaces",
]


def main() -> None:
    """CLI entry point."""
    print("vcoding - Virtualized development environment orchestration tool")
    print(f"Version: {__version__}")
    print()
    print("Usage:")
    print("  vcoding init [path]      - Initialize a new workspace")
    print("  vcoding start [path]     - Start the workspace container")
    print("  vcoding stop [path]      - Stop the workspace container")
    print("  vcoding destroy [path]   - Destroy the workspace container")
    print("  vcoding exec <command>   - Execute a command in the container")
    print()
    print("For more information, see the documentation or use Python API:")
    print("  from vcoding import create_workspace, start_workspace")
