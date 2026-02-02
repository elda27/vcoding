#!/usr/bin/env python3
"""Git workflow example.

This example demonstrates Git operations in vcoding:
- Initializing Git repository
- Committing changes
- Listing commits
- Rolling back changes
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import (
    commit_changes,
    create_workspace,
    destroy_workspace,
    get_commits,
    rollback,
    workspace_context,
)


def git_initialization() -> None:
    """Demonstrate Git initialization."""
    project_dir = Path(mkdtemp(prefix="vcoding_git_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        # Git is auto-initialized when creating workspace
        workspace = create_workspace(target=project_dir)

        # Check if Git is initialized
        print(f"Git initialized: {workspace.git.is_initialized}")
        print(f"Git directory: {workspace.git.repo_path}")

    finally:
        destroy_workspace(workspace)
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def commit_workflow() -> None:
    """Demonstrate commit workflow."""
    project_dir = Path(mkdtemp(prefix="vcoding_commit_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Create initial file
            (project_dir / "main.py").write_text('print("Version 1")\n')

            # Commit initial version
            commit1 = commit_changes(ws, "Initial commit")
            print(f"Initial commit: {commit1[:7] if commit1 else 'No changes'}")

            # Modify file
            (project_dir / "main.py").write_text('print("Version 2")\n')
            (project_dir / "utils.py").write_text("def helper(): pass\n")

            # Commit changes
            commit2 = commit_changes(ws, "Add utils and update main")
            print(f"Second commit: {commit2[:7] if commit2 else 'No changes'}")

            # Add more changes
            (project_dir / "main.py").write_text('print("Version 3")\n')

            commit3 = commit_changes(ws, "Update to version 3")
            print(f"Third commit: {commit3[:7] if commit3 else 'No changes'}")

            # List commits
            print("\n=== Commit History ===")
            commits = get_commits(ws, max_count=10)
            for commit in commits:
                print(f"  {commit.hash[:7]} - {commit.message}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def rollback_example() -> None:
    """Demonstrate rollback functionality."""
    project_dir = Path(mkdtemp(prefix="vcoding_rollback_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Create and commit version 1
            (project_dir / "config.py").write_text("DEBUG = False\nVERSION = '1.0.0'\n")
            commit1 = commit_changes(ws, "Version 1.0.0")
            print(f"Committed v1.0.0: {commit1[:7] if commit1 else 'N/A'}")

            # Create and commit version 2
            (project_dir / "config.py").write_text("DEBUG = True\nVERSION = '2.0.0'\n")
            commit2 = commit_changes(ws, "Version 2.0.0")
            print(f"Committed v2.0.0: {commit2[:7] if commit2 else 'N/A'}")

            # Create and commit version 3 (broken)
            (project_dir / "config.py").write_text("DEBUG = True\nVERSION = '3.0.0-broken'\n")
            commit3 = commit_changes(ws, "Version 3.0.0 (broken)")
            print(f"Committed v3.0.0: {commit3[:7] if commit3 else 'N/A'}")

            # Current state
            print(f"\nCurrent content:\n{(project_dir / 'config.py').read_text()}")

            # Rollback to v2.0.0
            if commit2:
                print(f"\n=== Rolling back to {commit2[:7]} ===")
                success = rollback(ws, commit2, hard=True)
                print(f"Rollback successful: {success}")

                # Check rolled back content
                print(f"\nContent after rollback:\n{(project_dir / 'config.py').read_text()}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def branch_workflow() -> None:
    """Demonstrate working with Git branches."""
    project_dir = Path(mkdtemp(prefix="vcoding_branch_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Create initial file
            (project_dir / "app.py").write_text("# Main application\n")
            commit_changes(ws, "Initial commit")

            # Get current branch
            current_branch = ws.git.get_current_branch()
            print(f"Current branch: {current_branch}")

            # Create feature branch (using GitPython directly)
            feature_branch = "feature/new-feature"
            ws.git.repo.create_head(feature_branch)
            ws.git.repo.heads[feature_branch].checkout()
            print(f"Created and switched to: {feature_branch}")

            # Make changes on feature branch
            (project_dir / "feature.py").write_text("def new_feature(): pass\n")
            commit_changes(ws, "Add new feature")

            # Switch back to main branch
            ws.git.repo.heads[current_branch].checkout()
            print(f"Switched back to: {current_branch}")

            # List branches
            print("\n=== Branches ===")
            for branch in ws.git.repo.branches:
                marker = "*" if branch.name == ws.git.get_current_branch() else " "
                print(f"  {marker} {branch.name}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Git Initialization ===\n")
    git_initialization()

    print("\n\n=== Commit Workflow ===\n")
    commit_workflow()

    print("\n\n=== Rollback Example ===\n")
    rollback_example()

    print("\n\n=== Branch Workflow ===\n")
    branch_workflow()
