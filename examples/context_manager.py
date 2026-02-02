#!/usr/bin/env python3
"""Context manager usage example.

This example demonstrates how to use workspace_context for
automatic workspace lifecycle management.
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import workspace_context


def simple_context_example() -> None:
    """Use workspace_context for automatic start/stop."""
    project_dir = Path(mkdtemp(prefix="vcoding_ctx_"))

    # Setup project
    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")
    (project_dir / "script.py").write_text('print("Hello from context!")\n')

    try:
        # workspace_context automatically starts and stops the workspace
        with workspace_context(project_dir) as ws:
            # Sync files
            ws.sync_to_container()

            # Execute commands
            exit_code, stdout, stderr = ws.execute("python script.py")
            print(f"Output: {stdout}")

            # Get container info
            print(f"Container ID: {ws.container_id}")
            print(f"Is running: {ws.is_running}")

        # Workspace is automatically stopped after exiting the context
        print("Workspace stopped automatically")

    finally:
        # Manual cleanup (optional - for complete removal)
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def auto_destroy_example() -> None:
    """Use auto_destroy to clean up workspace on exit."""
    project_dir = Path(mkdtemp(prefix="vcoding_destroy_"))

    # Setup
    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        # With auto_destroy=True, workspace is completely destroyed on exit
        with workspace_context(project_dir, auto_destroy=True) as ws:
            exit_code, stdout, stderr = ws.execute("echo 'This workspace will be destroyed'")
            print(f"Output: {stdout}")

        print("Workspace destroyed automatically")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def nested_operations_example() -> None:
    """Execute multiple operations within a context."""
    project_dir = Path(mkdtemp(prefix="vcoding_nested_"))

    # Setup a Python project
    (project_dir / "Dockerfile").write_text(
        """FROM python:3.11-slim
RUN pip install requests
WORKDIR /workspace
"""
    )
    (project_dir / "main.py").write_text(
        """
import sys
print(f"Python: {sys.version}")
print("All dependencies ready!")
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            # Sync project files
            ws.sync_to_container()

            # Install additional packages
            ws.execute("pip install pytest --quiet")

            # Run tests or scripts
            exit_code, stdout, stderr = ws.execute("python main.py")
            print(stdout)

            # Check installed packages
            exit_code, stdout, stderr = ws.execute("pip list | head -10")
            print(f"Installed packages:\n{stdout}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Simple Context Example ===\n")
    simple_context_example()

    print("\n\n=== Auto Destroy Example ===\n")
    auto_destroy_example()

    print("\n\n=== Nested Operations Example ===\n")
    nested_operations_example()
