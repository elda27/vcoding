"""Application data directory and path utilities."""

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_app_data_dir() -> Path:
    """Get the application data directory based on OS.

    Returns:
        Path to the application data directory.
        - Linux/macOS: ~/.vcoding
        - Windows: %APPDATA%/vcoding
    """
    system = platform.system()

    if system == "Windows":
        # Windows: %APPDATA%/vcoding
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "vcoding"
        else:
            # Fallback to user home
            return Path.home() / "AppData" / "Roaming" / "vcoding"
    else:
        # Linux/macOS: ~/.vcoding (hidden directory)
        return Path.home() / ".vcoding"


def get_workspaces_dir() -> Path:
    """Get the workspaces directory.

    Returns:
        Path to the workspaces directory.
    """
    return get_app_data_dir() / "workspaces"


def compute_target_hash(target_path: Path) -> str:
    """Compute SHA-256 hash of the target path.

    Args:
        target_path: Target file or directory path.

    Returns:
        SHA-256 hash string (hex).
    """
    # Normalize path: resolve to absolute, use forward slashes
    normalized = str(target_path.resolve()).replace("\\", "/")
    # Remove trailing slash for consistency
    normalized = normalized.rstrip("/")

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_workspace_dir(target_path: Path) -> Path:
    """Get the workspace directory for a target path.

    Uses hash-based directory structure:
    - First 2 characters as parent directory
    - Full hash as child directory

    Args:
        target_path: Target file or directory path.

    Returns:
        Path to the workspace directory.
    """
    target_hash = compute_target_hash(target_path)
    prefix = target_hash[:2]
    return get_workspaces_dir() / prefix / target_hash


class WorkspaceMetadata:
    """Manages workspace metadata."""

    def __init__(self, workspace_dir: Path) -> None:
        """Initialize metadata manager.

        Args:
            workspace_dir: Path to the workspace directory.
        """
        self._workspace_dir = workspace_dir
        self._metadata_path = workspace_dir / "metadata.json"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load metadata from file."""
        if self._metadata_path.exists():
            try:
                self._data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        """Save metadata to file."""
        self._workspace_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_path.write_text(
            json.dumps(self._data, indent=2, default=str),
            encoding="utf-8",
        )

    @property
    def target_path(self) -> Path | None:
        """Get the target path."""
        path = self._data.get("target_path")
        return Path(path) if path else None

    @target_path.setter
    def target_path(self, value: Path) -> None:
        """Set the target path."""
        self._data["target_path"] = str(value.resolve())

    @property
    def target_type(self) -> str | None:
        """Get the target type ('file' or 'directory')."""
        return self._data.get("target_type")

    @target_type.setter
    def target_type(self, value: str) -> None:
        """Set the target type."""
        if value not in ("file", "directory"):
            raise ValueError("target_type must be 'file' or 'directory'")
        self._data["target_type"] = value

    @property
    def created_at(self) -> datetime | None:
        """Get the creation timestamp."""
        ts = self._data.get("created_at")
        if ts:
            return datetime.fromisoformat(ts)
        return None

    @property
    def last_accessed(self) -> datetime | None:
        """Get the last access timestamp."""
        ts = self._data.get("last_accessed")
        if ts:
            return datetime.fromisoformat(ts)
        return None

    @property
    def synced_files(self) -> list[dict[str, str]]:
        """Get the list of synced files."""
        return self._data.get("synced_files", [])

    def initialize(self, target_path: Path) -> None:
        """Initialize metadata for a new workspace.

        Args:
            target_path: Target file or directory path.
        """
        target_path = target_path.resolve()
        now = datetime.now(timezone.utc).isoformat()

        self._data = {
            "target_path": str(target_path),
            "target_type": "file" if target_path.is_file() else "directory",
            "created_at": now,
            "last_accessed": now,
            "synced_files": [],
        }
        self._save()

    def update_last_accessed(self) -> None:
        """Update the last accessed timestamp."""
        self._data["last_accessed"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def add_synced_file(self, source: Path, destination: str) -> None:
        """Add a synced file record.

        Args:
            source: Source path on host.
            destination: Destination path in container.
        """
        synced = self._data.setdefault("synced_files", [])

        # Check if already exists
        source_str = str(source.resolve())
        for entry in synced:
            if entry["source"] == source_str:
                entry["destination"] = destination
                self._save()
                return

        # Add new entry
        synced.append(
            {
                "source": source_str,
                "destination": destination,
            }
        )
        self._save()

    def remove_synced_file(self, source: Path) -> bool:
        """Remove a synced file record.

        Args:
            source: Source path on host.

        Returns:
            True if removed, False if not found.
        """
        synced = self._data.get("synced_files", [])
        source_str = str(source.resolve())

        for i, entry in enumerate(synced):
            if entry["source"] == source_str:
                synced.pop(i)
                self._save()
                return True

        return False

    def prune_synced_files(self) -> list[str]:
        """Remove synced file records for non-existent source files.

        Returns:
            List of removed source paths.
        """
        synced = self._data.get("synced_files", [])
        removed: list[str] = []
        remaining: list[dict[str, str]] = []

        for entry in synced:
            source_path = Path(entry["source"])
            if source_path.exists():
                remaining.append(entry)
            else:
                removed.append(entry["source"])

        if removed:
            self._data["synced_files"] = remaining
            self._save()

        return removed

    def save(self) -> None:
        """Save metadata to file."""
        self._save()

    def exists(self) -> bool:
        """Check if metadata file exists."""
        return self._metadata_path.exists()


def list_workspaces() -> list[dict[str, Any]]:
    """List all workspaces.

    Returns:
        List of workspace information dictionaries.
    """
    workspaces_dir = get_workspaces_dir()
    result: list[dict[str, Any]] = []

    if not workspaces_dir.exists():
        return result

    for prefix_dir in workspaces_dir.iterdir():
        if not prefix_dir.is_dir() or len(prefix_dir.name) != 2:
            continue

        for ws_dir in prefix_dir.iterdir():
            if not ws_dir.is_dir():
                continue

            metadata = WorkspaceMetadata(ws_dir)
            if metadata.exists():
                result.append(
                    {
                        "workspace_dir": ws_dir,
                        "target_path": metadata.target_path,
                        "target_type": metadata.target_type,
                        "created_at": metadata.created_at,
                        "last_accessed": metadata.last_accessed,
                    }
                )

    return result


def find_orphaned_workspaces() -> list[Path]:
    """Find workspaces whose target paths no longer exist.

    Returns:
        List of orphaned workspace directories.
    """
    orphaned: list[Path] = []

    for ws_info in list_workspaces():
        target_path = ws_info.get("target_path")
        if target_path and not target_path.exists():
            orphaned.append(ws_info["workspace_dir"])

    return orphaned


def cleanup_orphaned_workspaces() -> int:
    """Remove orphaned workspaces.

    Returns:
        Number of removed workspaces.
    """
    import shutil

    orphaned = find_orphaned_workspaces()
    for ws_dir in orphaned:
        shutil.rmtree(ws_dir, ignore_errors=True)

        # Clean up empty parent directory
        parent = ws_dir.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    return len(orphaned)
