"""Example 03: Advanced API - Full control over workspace lifecycle.

Goal: Demonstrate manual workspace lifecycle management for advanced use cases.

This example demonstrates:
- Creating workspace with explicit configuration
- Manual start/stop lifecycle control
- Low-level execute with custom options
- Selective file syncing
- Custom commit messages
"""

from pathlib import Path

import vcoding


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    pass


def main():
    """Advanced API for full control over workspace lifecycle."""
    print("vcoding Example 03: Advanced API (Full Control)")
    print("=" * 50)

    # Setup: Create project directory
    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)
    (target_path / "README.md").write_text("# My Project\n")

    # Step 1: Create workspace with explicit configuration
    print("\n[Step 1] Creating workspace...")
    workspace = vcoding.create_workspace(
        target=target_path,
        name="codegen-example",
        language="python",
    )
    print(f"Workspace ID: {workspace.workspace_id}")

    try:
        # Step 2: Manual lifecycle control
        print("\n[Step 2] Starting workspace...")
        workspace.start()
        print("Workspace started")

        # Step 3: Sync files to container
        print("\n[Step 3] Syncing files to container...")
        workspace.sync_to_container()
        print("Files synced")

        # Step 4: Execute command with custom options
        print("\n[Step 4] Executing command...")
        exit_code, stdout, stderr = workspace.execute(
            "python -c 'from fibonacci import fibonacci; print(fibonacci(10))'",
            workdir="/workspace",
            timeout=30,
        )
        print(f"Exit code: {exit_code}")
        print(f"Fibonacci(10) = {stdout.strip()}")

        if stderr:
            print(f"Errors: {stderr}")

        if exit_code != 0:
            raise CommandExecutionError(
                f"Command execution failed.\n"
                f"Exit code: {exit_code}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )

        # Step 5: Sync files back from container
        print("\n[Step 5] Syncing files from container...")
        workspace.sync_from_container()
        print("Files synced back")

        # Step 6: Commit with custom message
        print("\n[Step 6] Committing changes...")
        commit_hash = workspace.commit_changes("Add generated code files")
        if commit_hash:
            print(f"Committed: {commit_hash[:8]}")
        else:
            print("No changes to commit")

    finally:
        # Always ensure workspace is stopped
        print("\n[Cleanup] Stopping workspace...")
        workspace.stop()
        print("Workspace stopped")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
