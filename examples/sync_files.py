#!/usr/bin/env python3
"""File synchronization example.

This example demonstrates:
- Syncing files to the container
- Syncing files from the container
- Managing sync history
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import sync_from_workspace, sync_to_workspace, workspace_context


def basic_sync() -> None:
    """Demonstrate basic file synchronization."""
    project_dir = Path(mkdtemp(prefix="vcoding_sync_"))
    output_dir = Path(mkdtemp(prefix="vcoding_output_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    # Create source files
    (project_dir / "src").mkdir()
    (project_dir / "src" / "main.py").write_text('print("Hello from main")\n')
    (project_dir / "src" / "utils.py").write_text("def helper(): return 42\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Sync entire project to container
            print("=== Syncing to container ===")
            sync_to_workspace(ws)
            print("Files synced to container")

            # Verify files exist in container
            exit_code, stdout, stderr = ws.execute("find /workspace -type f")
            print(f"Files in container:\n{stdout}")

            # Modify files in container
            ws.execute('echo "# Modified in container" >> /workspace/src/main.py')

            # Create new file in container
            ws.execute('echo "generated = True" > /workspace/src/generated.py')

            # Sync back to host
            print("\n=== Syncing from container ===")
            sync_from_workspace(ws, output_dir)
            print(f"Files synced to: {output_dir}")

            # Check synced files
            print("\n=== Synced files ===")
            for file in output_dir.rglob("*"):
                if file.is_file():
                    print(f"  {file.relative_to(output_dir)}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)


def selective_sync() -> None:
    """Demonstrate selective file synchronization."""
    project_dir = Path(mkdtemp(prefix="vcoding_selective_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    # Create a larger project structure
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "data").mkdir()

    (project_dir / "src" / "app.py").write_text("# App code\n")
    (project_dir / "tests" / "test_app.py").write_text("# Tests\n")
    (project_dir / "data" / "large_file.csv").write_text("a,b,c\n" * 1000)

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Sync only specific directories
            print("=== Syncing specific paths ===")

            # Sync src directory
            ws.copy_to_container(
                project_dir / "src",
                "/workspace/src",
            )
            print("Synced: src/")

            # Sync tests directory
            ws.copy_to_container(
                project_dir / "tests",
                "/workspace/tests",
            )
            print("Synced: tests/")

            # Skip data directory (too large)
            print("Skipped: data/ (too large)")

            # Verify
            exit_code, stdout, stderr = ws.execute("ls -la /workspace/")
            print(f"\nContainer workspace:\n{stdout}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def sync_history_management() -> None:
    """Demonstrate sync history management."""
    project_dir = Path(mkdtemp(prefix="vcoding_history_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    (project_dir / "file1.py").write_text("# File 1\n")
    (project_dir / "file2.py").write_text("# File 2\n")
    (project_dir / "file3.py").write_text("# File 3\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Sync files (recorded in sync history)
            ws.copy_to_container(project_dir / "file1.py", "/workspace/file1.py")
            ws.copy_to_container(project_dir / "file2.py", "/workspace/file2.py")
            ws.copy_to_container(project_dir / "file3.py", "/workspace/file3.py")

            print("=== Synced Files (recorded) ===")
            synced = ws.manager.get_synced_files()
            for entry in synced:
                print(f"  {entry['source']} -> {entry['destination']}")

            # Remove a local file (simulating deletion)
            (project_dir / "file2.py").unlink()
            print("\nDeleted local file: file2.py")

            # Prune sync history (removes references to non-existent files)
            removed = ws.prune_synced_files()
            print(f"\n=== Pruned entries: {removed} ===")

            # Show remaining sync history
            print("\n=== Remaining Synced Files ===")
            synced = ws.manager.get_synced_files()
            for entry in synced:
                print(f"  {entry['source']} -> {entry['destination']}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def auto_resync_on_restart() -> None:
    """Demonstrate automatic resync on workspace restart."""
    project_dir = Path(mkdtemp(prefix="vcoding_resync_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")
    (project_dir / "important.py").write_text("# Important code\n")

    try:
        # First session: sync files
        with workspace_context(project_dir) as ws:
            ws.copy_to_container(project_dir / "important.py", "/workspace/important.py")
            print("=== First session: synced important.py ===")

            exit_code, stdout, stderr = ws.execute("cat /workspace/important.py")
            print(f"Content in container:\n{stdout}")

        # Workspace stopped (but not destroyed)
        print("\n=== Workspace stopped ===")

        # Update local file
        (project_dir / "important.py").write_text("# Important code - updated!\n")
        print("Updated local file")

        # Second session: files are auto-resynced from sync history
        with workspace_context(project_dir) as ws:
            print("\n=== Second session: auto-resynced ===")

            exit_code, stdout, stderr = ws.execute("cat /workspace/important.py")
            print(f"Content in container (auto-resynced):\n{stdout}")

    finally:
        # Cleanup
        from vcoding import create_workspace, destroy_workspace

        ws = create_workspace(target=project_dir)
        destroy_workspace(ws)

        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Basic Sync ===\n")
    basic_sync()

    print("\n\n=== Selective Sync ===\n")
    selective_sync()

    print("\n\n=== Sync History Management ===\n")
    sync_history_management()

    print("\n\n=== Auto Resync on Restart ===\n")
    auto_resync_on_restart()
