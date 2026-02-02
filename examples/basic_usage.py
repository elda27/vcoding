#!/usr/bin/env python3
"""Basic vcoding usage example.

This example demonstrates how to:
- Create a workspace
- Start the virtual environment
- Execute commands
- Stop and destroy the workspace
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import (
    create_workspace,
    destroy_workspace,
    execute_command,
    start_workspace,
    stop_workspace,
)


def basic_workflow() -> None:
    """Demonstrate basic vcoding workflow."""
    # Create a temporary project directory
    project_dir = Path(mkdtemp(prefix="vcoding_example_"))
    print(f"Project directory: {project_dir}")

    # Create a simple Python file
    (project_dir / "hello.py").write_text('print("Hello from vcoding!")\n')

    # Create Dockerfile for the project
    (project_dir / "Dockerfile").write_text(
        """FROM python:3.11-slim
WORKDIR /workspace
"""
    )

    try:
        # Step 1: Create workspace
        print("\n=== Creating workspace ===")
        workspace = create_workspace(target=project_dir)
        print(f"Workspace created: {workspace.name}")

        # Step 2: Start workspace (builds container and starts SSH)
        print("\n=== Starting workspace ===")
        workspace = start_workspace(target=project_dir)
        print(f"Container started: {workspace.container_id}")

        # Step 3: Sync files to container
        print("\n=== Syncing files ===")
        workspace.sync_to_container()
        print("Files synced to container")

        # Step 4: Execute commands
        print("\n=== Executing commands ===")

        # Run Python file
        exit_code, stdout, stderr = execute_command(workspace, "python hello.py")
        print(f"Output: {stdout}")

        # Check Python version
        exit_code, stdout, stderr = execute_command(workspace, "python --version")
        print(f"Python version: {stdout}")

        # List files in workspace
        exit_code, stdout, stderr = execute_command(workspace, "ls -la")
        print(f"Workspace contents:\n{stdout}")

        # Step 5: Stop workspace
        print("\n=== Stopping workspace ===")
        stop_workspace(workspace)
        print("Workspace stopped")

    finally:
        # Cleanup: Destroy workspace
        print("\n=== Cleaning up ===")
        workspace = create_workspace(target=project_dir)
        destroy_workspace(workspace)
        print("Workspace destroyed")

        # Remove temp directory
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)
        print(f"Removed temp directory: {project_dir}")


def workspace_with_options() -> None:
    """Demonstrate workspace with custom options."""
    from vcoding import WorkspaceConfig
    from vcoding.core.types import DockerConfig, SshConfig

    project_dir = Path(mkdtemp(prefix="vcoding_custom_"))

    # Create Dockerfile
    (project_dir / "Dockerfile").write_text(
        """FROM node:20-slim
WORKDIR /app
"""
    )

    # Create custom configuration
    config = WorkspaceConfig(
        name="custom-workspace",
        target_path=str(project_dir),
        docker=DockerConfig(
            work_dir="/app",
            auto_remove=True,
        ),
        ssh=SshConfig(
            port=2222,
        ),
    )

    try:
        workspace = create_workspace(
            target=project_dir,
            name="my-custom-workspace",
            config=config,
        )
        workspace = start_workspace(target=project_dir)

        # Execute Node.js command
        exit_code, stdout, stderr = workspace.execute("node --version")
        print(f"Node.js version: {stdout}")

        stop_workspace(workspace)
    finally:
        workspace = create_workspace(target=project_dir)
        destroy_workspace(workspace)

        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Basic vcoding Usage ===\n")
    basic_workflow()

    print("\n\n=== Workspace with Custom Options ===\n")
    workspace_with_options()
