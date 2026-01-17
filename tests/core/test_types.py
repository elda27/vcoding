"""Tests for vcoding.core.types module."""

from pathlib import Path

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT
from vcoding.core.types import (
    ContainerState,
    DockerConfig,
    GitConfig,
    SSHConfig,
    VirtualizationType,
    WorkspaceConfig,
)


class TestVirtualizationType:
    """Tests for VirtualizationType enum."""

    def test_docker_value(self) -> None:
        """Test Docker virtualization type value."""
        assert VirtualizationType.DOCKER.value == "docker"

    def test_vagrant_value(self) -> None:
        """Test Vagrant virtualization type value."""
        assert VirtualizationType.VAGRANT.value == "vagrant"


class TestContainerState:
    """Tests for ContainerState enum."""

    def test_all_states(self) -> None:
        """Test all container states exist."""
        states = [
            ContainerState.STOPPED,
            ContainerState.RUNNING,
            ContainerState.PAUSED,
            ContainerState.NOT_FOUND,
            ContainerState.ERROR,
        ]
        assert len(states) == 5

    def test_state_values(self) -> None:
        """Test container state values."""
        assert ContainerState.RUNNING.value == "running"
        assert ContainerState.STOPPED.value == "stopped"


class TestSSHConfig:
    """Tests for SSHConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default SSH configuration values."""
        config = SSHConfig()
        assert config.host == "localhost"
        assert config.port == 22
        assert config.username == "vcoding"
        assert config.private_key_path is None
        assert config.timeout == 30

    def test_custom_values(self) -> None:
        """Test custom SSH configuration values."""
        config = SSHConfig(
            host="192.168.1.100",
            port=2222,
            username="testuser",
            private_key_path=Path("/path/to/key"),
            timeout=60,
        )
        assert config.host == "192.168.1.100"
        assert config.port == 2222
        assert config.username == "testuser"
        assert config.private_key_path == Path("/path/to/key")
        assert config.timeout == 60


class TestDockerConfig:
    """Tests for DockerConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default Docker configuration values."""
        config = DockerConfig()
        assert config.base_image == VCODING_DOCKER_OS_DEFAULT
        assert config.dockerfile_path is None
        assert config.container_name_prefix == "vcoding"
        assert config.ssh_port == 22
        assert config.work_dir == "/workspace"
        assert config.user == "vcoding"

    def test_custom_values(self) -> None:
        """Test custom Docker configuration values."""
        config = DockerConfig(
            base_image="python:3.12",
            container_name_prefix="myapp",
            work_dir="/app",
            user="developer",
        )
        assert config.base_image == "python:3.12"
        assert config.container_name_prefix == "myapp"
        assert config.work_dir == "/app"
        assert config.user == "developer"


class TestGitConfig:
    """Tests for GitConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default Git configuration values."""
        config = GitConfig()
        assert config.auto_init is True
        assert config.auto_commit is True
        assert "__pycache__/" in config.default_gitignore
        assert "*.pyc" in config.default_gitignore

    def test_custom_gitignore(self) -> None:
        """Test custom gitignore patterns."""
        config = GitConfig(
            default_gitignore=["*.log", "temp/"],
        )
        assert config.default_gitignore == ["*.log", "temp/"]


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig dataclass."""

    def test_minimal_config(self, temp_dir: Path) -> None:
        """Test minimal workspace configuration."""
        config = WorkspaceConfig(
            name="test",
            host_project_path=temp_dir,
        )
        assert config.name == "test"
        assert config.host_project_path == temp_dir
        assert config.virtualization_type == VirtualizationType.DOCKER
        assert config.temp_dir == temp_dir / ".vcoding"

    def test_string_path_conversion(self, temp_dir: Path) -> None:
        """Test that string paths are converted to Path objects."""
        config = WorkspaceConfig(
            name="test",
            host_project_path=str(temp_dir),  # type: ignore
        )
        assert isinstance(config.host_project_path, Path)

    def test_full_config(self, temp_dir: Path) -> None:
        """Test full workspace configuration."""
        custom_temp = temp_dir / "custom_temp"
        config = WorkspaceConfig(
            name="full-test",
            host_project_path=temp_dir,
            virtualization_type=VirtualizationType.DOCKER,
            docker=DockerConfig(base_image="alpine:latest"),
            ssh=SSHConfig(port=2222),
            git=GitConfig(auto_commit=False),
            temp_dir=custom_temp,
        )
        assert config.name == "full-test"
        assert config.docker.base_image == "alpine:latest"
        assert config.ssh.port == 2222
        assert config.git.auto_commit is False
        assert config.temp_dir == custom_temp
