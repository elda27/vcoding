#!/usr/bin/env python3
"""Claude Code CLI usage example.

This example demonstrates how to run Claude Code CLI
in a vcoding workspace.

Prerequisites:
- Claude Code CLI must be installed in the container
- Authentication must be configured
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import run_agent, workspace_context


def claudecode_basic_example() -> None:
    """Basic Claude Code usage."""
    project_dir = Path(mkdtemp(prefix="vcoding_claude_"))

    # Dockerfile with Claude Code CLI
    (project_dir / "Dockerfile").write_text(
        """FROM node:20-slim

# Install dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    openssh-server \\
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (hypothetical package name)
# RUN npm install -g @anthropic/claude-code

WORKDIR /workspace
"""
    )

    # Sample code to analyze
    (project_dir / "utils.py").write_text(
        """
def process_data(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result


def filter_and_transform(data, threshold):
    filtered = [x for x in data if x >= threshold]
    return [x ** 2 for x in filtered]
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            ws.sync_to_container()

            # Use Claude Code for code analysis
            result = run_agent(
                ws,
                agent_type="claudecode",
                prompt="Review the code in utils.py and suggest improvements",
                workdir="/workspace",
            )

            if result.success:
                print(f"Claude Code response:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def claudecode_refactoring_example() -> None:
    """Use Claude Code for refactoring tasks."""
    project_dir = Path(mkdtemp(prefix="vcoding_claude_refactor_"))

    (project_dir / "Dockerfile").write_text(
        """FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl git openssh-server nodejs npm
WORKDIR /workspace
"""
    )

    # Legacy code to refactor
    (project_dir / "legacy.py").write_text(
        """
# Old-style Python code
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_item(self, item):
        self.data.append(item)
    
    def process(self):
        result = []
        for i in range(len(self.data)):
            item = self.data[i]
            if type(item) == int:
                result.append(item * 2)
            elif type(item) == str:
                result.append(item.upper())
        return result
    
    def get_stats(self):
        nums = []
        for item in self.data:
            if type(item) == int:
                nums.append(item)
        if len(nums) == 0:
            return None
        total = 0
        for n in nums:
            total = total + n
        avg = total / len(nums)
        return {"count": len(nums), "sum": total, "avg": avg}
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            ws.sync_to_container()

            # Ask Claude Code to refactor
            result = run_agent(
                ws,
                agent_type="claudecode",
                prompt="Refactor legacy.py to use modern Python idioms",
            )

            if result.success:
                print(f"Refactoring suggestions:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def claudecode_test_generation() -> None:
    """Use Claude Code to generate tests."""
    project_dir = Path(mkdtemp(prefix="vcoding_claude_test_"))

    (project_dir / "Dockerfile").write_text(
        """FROM python:3.11-slim
RUN pip install pytest
RUN apt-get update && apt-get install -y git openssh-server
WORKDIR /workspace
"""
    )

    # Code to generate tests for
    (project_dir / "calculator.py").write_text(
        """
class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    def power(self, base: float, exponent: int) -> float:
        return base ** exponent
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            ws.sync_to_container()

            # Ask Claude Code to generate tests
            result = run_agent(
                ws,
                agent_type="claudecode",
                prompt="Generate pytest tests for the Calculator class in calculator.py",
            )

            if result.success:
                print(f"Generated tests:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Claude Code Basic Example ===\n")
    print("(Note: Requires Claude Code CLI installation and authentication)\n")
    # claudecode_basic_example()

    print("\n=== Claude Code Refactoring Example ===\n")
    # claudecode_refactoring_example()

    print("\n=== Claude Code Test Generation ===\n")
    # claudecode_test_generation()

    print(
        "Uncomment the function calls above after setting up "
        "Claude Code CLI authentication."
    )
