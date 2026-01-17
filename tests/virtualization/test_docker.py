"""Tests for vcoding.virtualization.docker module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vcoding.core.env import has_docker_daemon
from vcoding.core.types import (
    ContainerState,
    DockerConfig,
    VirtualizationType,
    WorkspaceConfig,
)


class TestDockerBackend:
    """Tests for DockerBackend class."""

    @pytest.fixture
    def sample_config(self, temp_dir: Path) -> WorkspaceConfig:
        """Create sample workspace config."""
        return WorkspaceConfig(
            name="test-workspace",
            host_project_path=temp_dir,
            virtualization_type=VirtualizationType.DOCKER,
            docker=DockerConfig(
                base_image="python:3.11-slim",
                ssh_port=2222,
                work_dir="/workspace",
            ),
        )

    @pytest.fixture
    def mock_docker_client(self) -> MagicMock:
        """Create mock docker client."""
        return MagicMock()

    @patch("docker.from_env")
    def test_init(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test initialization."""
        from vcoding.virtualization.docker import DockerBackend

        mock_from_env.return_value = MagicMock()
        backend = DockerBackend(sample_config)

        assert backend.config == sample_config
        mock_from_env.assert_called_once()

    @patch("docker.from_env")
    def test_build(
        self,
        mock_from_env: MagicMock,
        sample_config: WorkspaceConfig,
        temp_dir: Path,
    ) -> None:
        """Test building an image."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_image = MagicMock()
        mock_image.id = "sha256:abc123"
        mock_client.images.build.return_value = (mock_image, [])
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        image_id = backend.build()

        assert image_id == "sha256:abc123"

    @patch("docker.from_env")
    def test_create(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test creating a container."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "container-789"
        mock_client.containers.create.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)

        # Mock build to return image ID
        with patch.object(backend, "build", return_value="image-123"):
            container_id = backend.create()

            assert container_id == "container-789"
            mock_client.containers.create.assert_called_once()

    @patch("docker.from_env")
    def test_start(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test starting a container."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        backend.start("container-123")

        mock_container.start.assert_called_once()

    @patch("docker.from_env")
    def test_stop(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test stopping a container."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        backend.stop("container-123", timeout=5)

        mock_container.stop.assert_called_once_with(timeout=5)

    @patch("docker.from_env")
    def test_destroy(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test destroying a container."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        backend.destroy("container-123")

        mock_container.remove.assert_called_once_with(force=True)

    @patch("docker.from_env")
    def test_execute(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test executing a command."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        # With demux=True, output is (stdout, stderr) tuple
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0, output=(b"hello world", b"")
        )
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        exit_code, stdout, stderr = backend.execute("container-123", "echo hello")

        assert exit_code == 0
        assert "hello" in stdout

    @patch("docker.from_env")
    def test_execute_with_workdir(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test executing with working directory."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        # With demux=True, output is (stdout, stderr) tuple
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0, output=(b"output", b"")
        )
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        backend.execute("container-123", "ls", workdir="/workspace")

        call_kwargs = mock_container.exec_run.call_args
        assert call_kwargs.kwargs.get("workdir") == "/workspace"

    @patch("docker.from_env")
    def test_get_logs(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test getting container logs."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = b"container logs"
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        logs = backend.get_logs("container-123", tail=50)

        assert logs == "container logs"
        mock_container.logs.assert_called_once_with(tail=50)

    @patch("docker.from_env")
    def test_get_state_running(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test get_state when container is running."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        state = backend.get_state("container-123")

        assert state == ContainerState.RUNNING

    @patch("docker.from_env")
    def test_get_state_stopped(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test get_state when container is stopped."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        state = backend.get_state("container-123")

        assert state == ContainerState.STOPPED

    @patch("docker.from_env")
    def test_get_state_not_found(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test get_state when container not found."""
        from docker.errors import NotFound

        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("not found")
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        state = backend.get_state("nonexistent")

        assert state == ContainerState.NOT_FOUND

    @patch("docker.from_env")
    def test_get_ssh_config(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test getting SSH configuration."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        # The implementation uses container.ports property
        mock_container.ports = {"22/tcp": [{"HostIp": "0.0.0.0", "HostPort": "2222"}]}
        mock_client.containers.get.return_value = mock_container
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        ssh_config = backend.get_ssh_config("container-123")

        assert ssh_config["host"] == "localhost"
        assert ssh_config["port"] == 2222
        assert ssh_config["username"] == "vcoding"

    @patch("docker.from_env")
    def test_list_instances(
        self, mock_from_env: MagicMock, sample_config: WorkspaceConfig
    ) -> None:
        """Test listing instances."""
        from vcoding.virtualization.docker import DockerBackend

        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "container-123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_client.containers.list.return_value = [mock_container]
        mock_from_env.return_value = mock_client

        backend = DockerBackend(sample_config)
        instances = backend.list_instances()

        assert isinstance(instances, list)


class TestDockerBackendIntegration:
    """Integration tests that require Docker."""

    @pytest.mark.skipif(not has_docker_daemon(), reason="Requires Docker daemon")
    def test_real_docker_workflow(self, temp_dir: Path) -> None:
        """Test real Docker workflow - requires Docker daemon."""
        from vcoding.virtualization.docker import DockerBackend

        config = WorkspaceConfig(
            name="integration-test",
            host_project_path=temp_dir,
            docker=DockerConfig(
                base_image="python:3.11-slim",
            ),
        )

        backend = DockerBackend(config)

        # Build
        image_id = backend.build()
        assert image_id is not None

        # Create
        container_id = backend.create(image_id)
        assert container_id is not None

        try:
            # Start
            backend.start(container_id)
            assert backend.get_state(container_id) == ContainerState.RUNNING

            # Execute
            exit_code, stdout, stderr = backend.execute(
                container_id, "python --version"
            )
            assert exit_code == 0
            assert "Python" in stdout

        finally:
            # Cleanup
            backend.stop(container_id)
            backend.destroy(container_id)
