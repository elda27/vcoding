"""Example 01: Code Generation - Using Code Agents in vcoding.

This example demonstrates:
- Simple one-shot API (recommended for most users)
- Context manager API (for multiple operations)
- Advanced API (for full control)
"""

from pathlib import Path

import vcoding


def simple_example():
    """Simplest way to generate code - single function call."""
    print("=== Simple One-Shot API ===")

    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)
    (target_path / "README.md").write_text("# My Project\n")

    # Generate code with a single call - no lifecycle management needed
    result = vcoding.generate(
        target="./my-project",
        prompt="Create a Python function that calculates fibonacci numbers",
        output="fibonacci.py",
    )
    print(f"Generation: {'success' if result.success else 'failed'}")

    # Run code with a single call
    exit_code, stdout, stderr = vcoding.run(
        target="./my-project",
        command="python -c 'from fibonacci import fibonacci; print(fibonacci(10))'",
    )
    print(f"Result: {stdout.strip()}")


def context_manager_example():
    """Use context manager for multiple operations."""
    print("\n=== Context Manager API ===")

    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)

    # Context manager handles start/stop and file syncing automatically
    with vcoding.workspace_context("./my-project", language="python") as ws:
        # Generate multiple files
        ws.generate("Create a fibonacci function", output="fibonacci.py")
        ws.generate("Create a todo list class", output="todo.py")

        # Run tests
        exit_code, stdout, stderr = ws.run("python -m pytest")
        print(f"Tests: {'passed' if exit_code == 0 else 'failed'}")

        # Commit changes
        commit_hash = ws.commit_changes("Add generated code")
        if commit_hash:
            print(f"Committed: {commit_hash[:8]}")


def advanced_example():
    """Advanced API for full control over workspace lifecycle."""
    print("\n=== Advanced API (Full Control) ===")

    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)
    (target_path / "README.md").write_text("# My Project\n")

    # Create workspace with explicit configuration
    workspace = vcoding.create_workspace(
        target=target_path,
        name="codegen-example",
        language="python",
    )
    print(f"Workspace ID: {workspace.workspace_id}")

    try:
        # Manual lifecycle control
        workspace.start()
        workspace.sync_to_container()

        # Use low-level execute with custom working directory
        exit_code, stdout, stderr = workspace.execute(
            "python -c 'from fibonacci import fibonacci; print(fibonacci(10))'",
            workdir="/workspace",
            timeout=30,
        )
        print(f"Fibonacci(10) = {stdout.strip()}")

        # Sync specific files back
        workspace.sync_from_container()

        # Commit with custom message
        commit_hash = workspace.commit_changes("Add generated code files")
        if commit_hash:
            print(f"Committed: {commit_hash[:8]}")

    finally:
        workspace.stop()
        print("Workspace stopped")


def main():
    """Run all examples."""
    print("vcoding Code Generation Examples")
    print("=" * 40)

    # Recommended for simple use cases
    simple_example()

    # Recommended for multiple operations
    context_manager_example()

    # For users who need full control
    advanced_example()


if __name__ == "__main__":
    main()
