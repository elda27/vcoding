"""Tests for vcoding.workspace.workspace module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vcoding.core.types import WorkspaceConfig
from vcoding.workspace.workspace import Workspace


class TestWorkspace:
    """Tests for Workspace class."""

    def test_init(self, temp_dir: Path) -> None:
        """Test initialization."""
        workspace = Workspace(temp_dir, name="test-ws")
        assert workspace.name == "test-ws"
        assert workspace.project_path == temp_dir

    def test_init_uses_directory_name(self, temp_dir: Path) -> None:
        """Test that directory name is used as workspace name."""
        workspace = Workspace(temp_dir)
        assert workspace.name == temp_dir.name

    def test_init_with_config(
        self, temp_dir: Path, sample_workspace_config: WorkspaceConfig
    ) -> None:
        """Test initialization with config."""
        workspace = Workspace(temp_dir, config=sample_workspace_config)
        assert workspace.config == sample_workspace_config

    def test_properties(self, temp_dir: Path) -> None:
        """Test basic properties."""
        workspace = Workspace(temp_dir, name="props-test")

        assert workspace.name == "props-test"
        assert workspace.project_path == temp_dir
        assert workspace.config is not None
        assert workspace.manager is not None
        assert workspace.container_id is None
        assert workspace.ssh is None
        assert workspace.is_running is False

    def test_git_property(self, temp_dir: Path) -> None:
        """Test git manager property."""
        workspace = Workspace(temp_dir)
        git = workspace.git

        assert git is not None
        assert git.repo_path == temp_dir

    def test_ssh_key_manager_property(self, temp_dir: Path) -> None:
        """Test SSH key manager property."""
        workspace = Workspace(temp_dir)
        workspace.initialize()

        key_manager = workspace.ssh_key_manager

        assert key_manager is not None
        assert key_manager.keys_dir.exists()

    def test_initialize(self, temp_dir: Path) -> None:
        """Test workspace initialization."""
        workspace = Workspace(temp_dir)
        workspace.initialize()

        assert workspace.manager._initialized is True
        assert workspace.manager.vcoding_dir.exists()

    def test_initialize_creates_git_repo(self, temp_dir: Path) -> None:
        """Test that initialize creates git repo when configured."""
        config = WorkspaceConfig(
            name="git-test",
            host_project_path=temp_dir,
        )
        workspace = Workspace(temp_dir, config=config)
        workspace.initialize()

        assert workspace.git.is_initialized is True

    @patch("vcoding.virtualization.docker.DockerBackend")
    def test_backend_property(
        self, mock_backend_class: MagicMock, temp_dir: Path
    ) -> None:
        """Test backend property creates Docker backend."""
        workspace = Workspace(temp_dir)

        # Access backend property
        with patch.object(workspace, "_create_backend") as mock_create:
            mock_backend = MagicMock()
            mock_create.return_value = mock_backend
            backend = workspace.backend

            assert backend == mock_backend

    def test_is_running_false(self, temp_dir: Path) -> None:
        """Test is_running when container not started."""
        workspace = Workspace(temp_dir)
        assert workspace.is_running is False

    def test_cleanup(self, temp_dir: Path) -> None:
        """Test workspace cleanup."""
        workspace = Workspace(temp_dir)
        workspace.initialize()

        # Create temp files
        temp_file = workspace.manager.temp_dir / "test.txt"
        temp_file.write_text("test", encoding="utf-8")

        workspace.cleanup()

        assert not temp_file.exists()

    def test_context_manager(self, temp_dir: Path) -> None:
        """Test workspace context manager interface."""
        workspace = Workspace(temp_dir)

        # Test that __enter__ and __exit__ exist
        assert hasattr(workspace, "__enter__")
        assert hasattr(workspace, "__exit__")


class TestWorkspaceWithMockedDocker:
    """Tests for Workspace with mocked Docker backend."""

    @pytest.fixture
    def mock_workspace(self, temp_dir: Path) -> Workspace:
        """Create workspace with mocked backend."""
        workspace = Workspace(temp_dir, name="mock-test")
        workspace.initialize()
        return workspace

    def test_start_mocked(self, mock_workspace: Workspace) -> None:
        """Test starting workspace - simplified mock test."""
        # This test verifies the interface but skips the full start flow
        # which requires complex mocking of Docker, SSH, and key management
        assert hasattr(mock_workspace, "start")
        assert callable(mock_workspace.start)

    def test_execute_not_started_raises(self, mock_workspace: Workspace) -> None:
        """Test that execute raises when not started."""
        with pytest.raises(RuntimeError, match="not started"):
            mock_workspace.execute("echo hello")

    def test_copy_to_container_not_started_raises(
        self, mock_workspace: Workspace
    ) -> None:
        """Test that copy_to_container raises when not started."""
        with pytest.raises(RuntimeError, match="not started"):
            mock_workspace.copy_to_container(Path("/local"), "/remote")

    def test_copy_from_container_not_started_raises(
        self, mock_workspace: Workspace
    ) -> None:
        """Test that copy_from_container raises when not started."""
        with pytest.raises(RuntimeError, match="not started"):
            mock_workspace.copy_from_container("/remote", Path("/local"))

    def test_get_agent_not_started_raises(self, mock_workspace: Workspace) -> None:
        """Test that get_agent raises when not started."""
        with pytest.raises(RuntimeError, match="not started"):
            mock_workspace.get_agent("copilot")

    def test_get_logs_not_started(self, mock_workspace: Workspace) -> None:
        """Test get_logs when not started."""
        logs = mock_workspace.get_logs()
        assert logs == ""
