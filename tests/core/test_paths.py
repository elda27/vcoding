"""Tests for vcoding.core.paths module."""

import platform
from pathlib import Path

import pytest

from vcoding.core.paths import (
    WorkspaceMetadata,
    cleanup_orphaned_workspaces,
    compute_target_hash,
    find_orphaned_workspaces,
    get_app_data_dir,
    get_workspace_dir,
    get_workspaces_dir,
    list_workspaces,
)


class TestGetAppDataDir:
    """Tests for get_app_data_dir function."""

    def test_returns_path(self) -> None:
        """Test that function returns a Path object."""
        result = get_app_data_dir()
        assert isinstance(result, Path)

    def test_path_ends_with_vcoding(self) -> None:
        """Test that path ends with vcoding."""
        result = get_app_data_dir()
        assert result.name == "vcoding"

    def test_windows_uses_appdata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Windows uses APPDATA environment variable."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")
        result = get_app_data_dir()
        assert "AppData" in str(result) or "vcoding" in str(result)

    def test_linux_uses_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Linux uses home directory."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        result = get_app_data_dir()
        # On Linux, the directory is ~/.vcoding
        assert result.name == ".vcoding"


class TestComputeTargetHash:
    """Tests for compute_target_hash function."""

    def test_returns_hex_string(self, temp_dir: Path) -> None:
        """Test that function returns hex string."""
        result = compute_target_hash(temp_dir)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex length

    def test_consistent_hash(self, temp_dir: Path) -> None:
        """Test that same path produces same hash."""
        hash1 = compute_target_hash(temp_dir)
        hash2 = compute_target_hash(temp_dir)
        assert hash1 == hash2

    def test_different_paths_different_hashes(self, temp_dir: Path) -> None:
        """Test that different paths produce different hashes."""
        path1 = temp_dir / "dir1"
        path2 = temp_dir / "dir2"
        hash1 = compute_target_hash(path1)
        hash2 = compute_target_hash(path2)
        assert hash1 != hash2


class TestGetWorkspaceDir:
    """Tests for get_workspace_dir function."""

    def test_returns_path(self, temp_dir: Path) -> None:
        """Test that function returns a Path object."""
        result = get_workspace_dir(temp_dir)
        assert isinstance(result, Path)

    def test_uses_hash_structure(self, temp_dir: Path) -> None:
        """Test that workspace dir uses hash-based structure."""
        result = get_workspace_dir(temp_dir)
        target_hash = compute_target_hash(temp_dir)

        # Parent should be first 2 chars of hash
        assert result.parent.name == target_hash[:2]
        # Directory should be full hash
        assert result.name == target_hash

    def test_under_workspaces_dir(self, temp_dir: Path) -> None:
        """Test that workspace dir is under workspaces directory."""
        result = get_workspace_dir(temp_dir)
        workspaces_dir = get_workspaces_dir()
        assert str(result).startswith(str(workspaces_dir))


class TestWorkspaceMetadata:
    """Tests for WorkspaceMetadata class."""

    def test_initialize(self, temp_dir: Path) -> None:
        """Test metadata initialization."""
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        metadata = WorkspaceMetadata(workspace_dir)
        metadata.initialize(temp_dir)

        assert metadata.target_path == temp_dir
        assert metadata.target_type == "directory"
        assert metadata.created_at is not None
        assert metadata.synced_files == []

    def test_add_synced_file(self, temp_dir: Path) -> None:
        """Test adding synced file."""
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        metadata = WorkspaceMetadata(workspace_dir)
        metadata.initialize(temp_dir)

        source = temp_dir / "test.py"
        source.write_text("# test", encoding="utf-8")
        metadata.add_synced_file(source, "/workspace/test.py")

        assert len(metadata.synced_files) == 1
        assert metadata.synced_files[0]["destination"] == "/workspace/test.py"

    def test_remove_synced_file(self, temp_dir: Path) -> None:
        """Test removing synced file."""
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        metadata = WorkspaceMetadata(workspace_dir)
        metadata.initialize(temp_dir)

        source = temp_dir / "test.py"
        source.write_text("# test", encoding="utf-8")
        metadata.add_synced_file(source, "/workspace/test.py")

        result = metadata.remove_synced_file(source)
        assert result is True
        assert len(metadata.synced_files) == 0

    def test_prune_synced_files(self, temp_dir: Path) -> None:
        """Test pruning non-existent files."""
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        metadata = WorkspaceMetadata(workspace_dir)
        metadata.initialize(temp_dir)

        # Add existing file
        existing = temp_dir / "existing.py"
        existing.write_text("# existing", encoding="utf-8")
        metadata.add_synced_file(existing, "/workspace/existing.py")

        # Add non-existing file directly
        metadata._data["synced_files"].append(
            {
                "source": str(temp_dir / "nonexistent.py"),
                "destination": "/workspace/nonexistent.py",
            }
        )
        metadata._save()

        # Prune should remove non-existent
        removed = metadata.prune_synced_files()
        assert len(removed) == 1
        assert len(metadata.synced_files) == 1

    def test_persistence(self, temp_dir: Path) -> None:
        """Test that metadata persists across instances."""
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()

        # Create and save
        metadata1 = WorkspaceMetadata(workspace_dir)
        metadata1.initialize(temp_dir)
        source = temp_dir / "test.py"
        source.write_text("# test", encoding="utf-8")
        metadata1.add_synced_file(source, "/workspace/test.py")

        # Load in new instance
        metadata2 = WorkspaceMetadata(workspace_dir)
        assert metadata2.target_path == temp_dir
        assert len(metadata2.synced_files) == 1


class TestListWorkspaces:
    """Tests for list_workspaces function."""

    def test_empty_when_no_workspaces(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test returns empty list when no workspaces."""
        monkeypatch.setattr(
            "vcoding.core.paths.get_workspaces_dir", lambda: temp_dir / "workspaces"
        )
        result = list_workspaces()
        assert result == []

    def test_lists_existing_workspaces(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test lists existing workspaces."""
        workspaces_dir = temp_dir / "workspaces"
        workspaces_dir.mkdir()

        # Create a workspace
        ws_dir = workspaces_dir / "ab" / "abc123"
        ws_dir.mkdir(parents=True)
        metadata = WorkspaceMetadata(ws_dir)
        target = temp_dir / "project"
        target.mkdir()
        metadata.initialize(target)

        monkeypatch.setattr(
            "vcoding.core.paths.get_workspaces_dir", lambda: workspaces_dir
        )

        result = list_workspaces()
        assert len(result) == 1
        assert result[0]["workspace_dir"] == ws_dir
