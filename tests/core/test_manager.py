"""Tests for vcoding.core.manager module."""

import json
from pathlib import Path

from vcoding.core.manager import WorkspaceManager
from vcoding.core.paths import get_workspace_dir
from vcoding.core.types import WorkspaceConfig


class TestWorkspaceManager:
    """Tests for WorkspaceManager class."""

    def test_init(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test initialization."""
        manager = WorkspaceManager(sample_workspace_config)
        assert manager.config == sample_workspace_config
        assert manager._initialized is False

    def test_from_target_new_project(self, temp_dir: Path) -> None:
        """Test creating manager from target without existing config."""
        manager = WorkspaceManager.from_target(temp_dir, "test-project")
        assert manager.config.name == "test-project"
        assert manager.config.target_path == temp_dir

    def test_from_target_existing_config(self, temp_dir: Path) -> None:
        """Test creating manager from target with existing config."""
        # Create existing config in workspace dir
        workspace_dir = get_workspace_dir(temp_dir)
        workspace_dir.mkdir(parents=True)
        config_path = workspace_dir / "config.json"
        config_data = {
            "name": "existing",
            "target_path": str(temp_dir),
            "target_type": "directory",
            "virtualization_type": "docker",
            "docker": {"base_image": "alpine:latest"},
            "ssh": {},
            "git": {},
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        manager = WorkspaceManager.from_target(temp_dir)
        assert manager.config.docker.base_image == "alpine:latest"

    def test_from_target_uses_directory_name(self, temp_dir: Path) -> None:
        """Test that directory name is used as workspace name."""
        manager = WorkspaceManager.from_target(temp_dir)
        assert manager.config.name == temp_dir.name

    def test_workspace_dir(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test workspace directory path."""
        manager = WorkspaceManager(sample_workspace_config)
        assert manager.workspace_dir == sample_workspace_config.workspace_dir

    def test_keys_dir(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test keys directory path."""
        manager = WorkspaceManager(sample_workspace_config)
        expected = sample_workspace_config.workspace_dir / "keys"
        assert manager.keys_dir == expected

    def test_temp_dir(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test temp directory path."""
        manager = WorkspaceManager(sample_workspace_config)
        expected = sample_workspace_config.workspace_dir / "temp"
        assert manager.temp_dir == expected

    def test_logs_dir(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test logs directory path."""
        manager = WorkspaceManager(sample_workspace_config)
        expected = sample_workspace_config.workspace_dir / "logs"
        assert manager.logs_dir == expected

    def test_ensure_directories(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test directory creation."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.ensure_directories()

        assert manager.workspace_dir.exists()
        assert manager.keys_dir.exists()
        assert manager.temp_dir.exists()
        assert manager.logs_dir.exists()

    def test_initialize(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test initialization."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.initialize()

        assert manager._initialized is True
        assert manager.workspace_dir.exists()

    def test_initialize_idempotent(
        self, sample_workspace_config: WorkspaceConfig
    ) -> None:
        """Test that initialize is idempotent."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.initialize()
        manager.initialize()  # Should not raise

        assert manager._initialized is True

    def test_cleanup(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test cleanup of temporary files."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.ensure_directories()

        # Create some temp files
        temp_file = manager.temp_dir / "test.txt"
        temp_file.write_text("test", encoding="utf-8")
        temp_subdir = manager.temp_dir / "subdir"
        temp_subdir.mkdir()
        (temp_subdir / "nested.txt").write_text("nested", encoding="utf-8")

        manager.cleanup()

        assert not temp_file.exists()
        assert not temp_subdir.exists()

    def test_save_config(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test saving configuration."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.ensure_directories()
        manager.save_config()

        config_path = manager.workspace_dir / "config.json"
        assert config_path.exists()

        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        assert loaded["name"] == sample_workspace_config.name
        assert loaded["virtualization_type"] == "docker"

    def test_synced_files_management(
        self, sample_workspace_config: WorkspaceConfig
    ) -> None:
        """Test synced files management."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.initialize()

        # Add synced file
        source = sample_workspace_config.target_path / "test.py"
        source.write_text("# test", encoding="utf-8")
        manager.add_synced_file(source, "/workspace/test.py")

        # Verify it's recorded
        synced = manager.get_synced_files()
        assert len(synced) == 1
        assert synced[0]["destination"] == "/workspace/test.py"

    def test_prune_synced_files(self, sample_workspace_config: WorkspaceConfig) -> None:
        """Test pruning non-existent synced files."""
        manager = WorkspaceManager(sample_workspace_config)
        manager.initialize()

        # Add synced file that doesn't exist
        fake_source = sample_workspace_config.target_path / "nonexistent.py"
        manager.metadata.add_synced_file(fake_source, "/workspace/nonexistent.py")

        # Prune should remove it
        removed = manager.prune_synced_files()
        assert len(removed) == 1
        assert manager.get_synced_files() == []


class TestWorkspaceManagerInit:
    """Tests for core/__init__.py imports."""

    def test_imports(self) -> None:
        """Test that core module exports are available."""
        from vcoding.core import (
            Config,
            ContainerState,
            VirtualizationType,
            WorkspaceConfig,
        )

        assert Config is not None
        assert ContainerState is not None
        assert VirtualizationType is not None
        assert WorkspaceConfig is not None
