"""Example 01: Simple One-Shot API - The easiest way to use vcoding.

Goal: Generate code with a single function call without lifecycle management.

This example demonstrates:
- Using vcoding.generate() for code generation
- Using vcoding.run() for command execution
- No manual resource management required

Prerequisites:
- Docker Desktop must be running
- ANTHROPIC_API_KEY environment variable must be set (for Claude Code)
"""

from pathlib import Path

import vcoding


class CodeGenerationError(Exception):
    """Raised when code generation fails."""

    pass


class CommandExecutionError(Exception):
    """Raised when command execution fails."""

    pass


def main():
    """Generate code using the simple one-shot API."""
    print("vcoding Example 01: Simple One-Shot API")
    print("=" * 50)

    # Setup: Create a minimal project directory
    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)
    (target_path / "README.md").write_text("# My Project\n")

    # Step 1: Generate code with a single call
    # No lifecycle management needed - vcoding handles everything
    print("\n[Step 1] Generating fibonacci.py...")
    result = vcoding.generate(
        target="./my-project",
        prompt="Create a Python function that calculates fibonacci numbers",
        output="fibonacci.py",
        language="python",  # Ensures Python is installed in the container
    )
    print(f"Generation: {'success' if result.success else 'failed'}")

    if not result.success:
        raise CodeGenerationError(
            f"Code generation failed.\n"
            f"Exit code: {result.exit_code}\n"
            f"Stderr: {result.stderr}"
        )

    # Step 2: Run the generated code
    print("\n[Step 2] Running generated code...")
    exit_code, stdout, stderr = vcoding.run(
        target="./my-project",
        command="python -c 'from fibonacci import fibonacci; print(fibonacci(10))'",
        language="python",  # Ensures Python is installed in the container
    )
    print(f"Exit code: {exit_code}")
    print(f"Result: {stdout.strip()}")

    if stderr:
        print(f"Errors: {stderr}")

    if exit_code != 0:
        raise CommandExecutionError(
            f"Command execution failed.\n"
            f"Exit code: {exit_code}\n"
            f"Stdout: {stdout}\n"
            f"Stderr: {stderr}"
        )

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
