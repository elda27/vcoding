#!/usr/bin/env python3
"""GitHub Copilot CLI usage example.

This example demonstrates how to run GitHub Copilot CLI
in a vcoding workspace.

Prerequisites:
- GitHub Copilot CLI must be installed in the container
- Authentication must be configured
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import run_agent, workspace_context


def copilot_suggest_example() -> None:
    """Get command suggestions from Copilot."""
    project_dir = Path(mkdtemp(prefix="vcoding_copilot_"))

    # Dockerfile with GitHub CLI and Copilot extension
    (project_dir / "Dockerfile").write_text(
        """FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    openssh-server \\
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \\
    dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \\
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt-get update && \\
    apt-get install -y gh

# Install GitHub Copilot CLI extension
RUN gh extension install github/gh-copilot || true

WORKDIR /workspace
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            # Use Copilot to suggest a command
            result = run_agent(
                ws,
                agent_type="copilot",
                prompt="How do I find all Python files modified in the last 24 hours?",
                options={"mode": "suggest"},
            )

            if result.success:
                print(f"Copilot suggestion:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def copilot_explain_example() -> None:
    """Get explanations from Copilot."""
    project_dir = Path(mkdtemp(prefix="vcoding_copilot_explain_"))

    (project_dir / "Dockerfile").write_text(
        """FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl git openssh-server
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \\
    dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \\
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt-get update && apt-get install -y gh
RUN gh extension install github/gh-copilot || true
WORKDIR /workspace
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            # Use Copilot to explain a command
            result = run_agent(
                ws,
                agent_type="copilot",
                prompt="What does 'find . -name \"*.py\" -exec grep -l \"import os\" {} \\;' do?",
                options={"mode": "explain"},
            )

            if result.success:
                print(f"Copilot explanation:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def copilot_code_assistance() -> None:
    """Use Copilot for code-related tasks."""
    project_dir = Path(mkdtemp(prefix="vcoding_copilot_code_"))

    (project_dir / "Dockerfile").write_text(
        """FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl git openssh-server
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \\
    dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \\
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt-get update && apt-get install -y gh
RUN gh extension install github/gh-copilot || true
WORKDIR /workspace
"""
    )

    # Sample Python code
    (project_dir / "app.py").write_text(
        """
def calculate_factorial(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    return n * calculate_factorial(n - 1)


def main():
    for i in range(10):
        print(f"{i}! = {calculate_factorial(i)}")


if __name__ == "__main__":
    main()
"""
    )

    try:
        with workspace_context(project_dir) as ws:
            ws.sync_to_container()

            # Ask Copilot for code review suggestions
            result = run_agent(
                ws,
                agent_type="copilot",
                prompt="How can I optimize the factorial function in app.py?",
            )

            if result.success:
                print(f"Copilot suggestion:\n{result.stdout}")
            else:
                print(f"Error: {result.stderr}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Copilot Suggest Example ===\n")
    print("(Note: Requires GitHub Copilot CLI authentication)\n")
    # copilot_suggest_example()

    print("\n=== Copilot Explain Example ===\n")
    # copilot_explain_example()

    print("\n=== Copilot Code Assistance ===\n")
    # copilot_code_assistance()

    print(
        "Uncomment the function calls above after setting up "
        "GitHub Copilot CLI authentication."
    )
