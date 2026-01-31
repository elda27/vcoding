"""Example 02: Context Manager API - Multiple operations with automatic resource management.

Goal: Use context manager to perform multiple code generation and execution operations.

This example demonstrates:
- Using vcoding.workspace_context() for automatic lifecycle management
- Generating multiple files in sequence
- Running tests
- Committing changes
"""

from pathlib import Path

import vcoding


class CodeGenerationError(Exception):
    """Raised when code generation fails."""

    pass


class TestExecutionError(Exception):
    """Raised when test execution fails."""

    pass


def main():
    """Use context manager for multiple operations."""
    print("vcoding Example 02: Context Manager API")
    print("=" * 50)

    # Setup: Create project directory
    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)

    # Context manager handles start/stop and file syncing automatically
    print("\n[Starting workspace context...]")

    with vcoding.workspace_context("./my-project", language="python") as ws:
        # Step 1: Generate multiple files
        print("\n[Step 1] Generating fibonacci.py...")
        result1 = ws.generate("Create a fibonacci function", output="fibonacci.py")
        if not result1.success:
            raise CodeGenerationError(
                f"Failed to generate fibonacci.py.\n"
                f"Exit code: {result1.exit_code}\n"
                f"Stderr: {result1.stderr}"
            )

        print("[Step 1] Generating todo.py...")
        result2 = ws.generate("Create a todo list class", output="todo.py")
        if not result2.success:
            raise CodeGenerationError(
                f"Failed to generate todo.py.\n"
                f"Exit code: {result2.exit_code}\n"
                f"Stderr: {result2.stderr}"
            )

        # Step 2: Run tests
        print("\n[Step 2] Running tests...")
        exit_code, stdout, stderr = ws.run("python -m pytest")
        print(f"Tests: {'passed' if exit_code == 0 else 'failed'}")

        if stdout:
            print(f"Output: {stdout[:200]}...")  # Show first 200 chars

        if exit_code != 0:
            raise TestExecutionError(
                f"Tests failed.\n"
                f"Exit code: {exit_code}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )

        # Step 3: Commit changes
        print("\n[Step 3] Committing changes...")
        commit_hash = ws.commit_changes("Add generated code")
        if commit_hash:
            print(f"Committed: {commit_hash[:8]}")
        else:
            print("No changes to commit")

    # Context manager automatically cleans up here
    print("\n[Workspace context closed]")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
