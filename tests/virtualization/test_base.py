"""Tests for vcoding.virtualization.base module."""

from pathlib import Path
from typing import Any


from vcoding.core.types import (
    ContainerState,
    VirtualizationType,
    WorkspaceConfig,
)
from vcoding.virtualization.base import VirtualizationBackend


class ConcreteBackend(VirtualizationBackend):
    """Concrete implementation for testing."""

    def __init__(self, config: WorkspaceConfig | None = None) -> None:
        """Initialize with default config."""
        if config is None:
            config = WorkspaceConfig(
                name="test",
                target_path=Path("/tmp/test"),
            )
        super().__init__(config)
        self._built = False
        self._created = False
        self._started = False

    def build(self, dockerfile_content: str | None = None) -> str:
        """Mock build."""
        self._built = True
        return "image-123"

    def create(self, image: str | None = None) -> str:
        """Mock create."""
        self._created = True
        return "container-456"

    def start(self, instance_id: str) -> None:
        """Mock start."""
        self._started = True

    def stop(self, instance_id: str, timeout: int = 10) -> None:
        """Mock stop."""
        self._started = False

    def destroy(self, instance_id: str) -> None:
        """Mock destroy."""
        self._created = False

    def get_state(self, instance_id: str) -> ContainerState:
        """Mock get_state."""
        if self._started:
            return ContainerState.RUNNING
        elif self._created:
            return ContainerState.STOPPED
        else:
            return ContainerState.NOT_FOUND

    def execute(
        self,
        instance_id: str,
        command: str | list[str],
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Mock execute."""
        return (0, "output", "")

    def copy_to(self, instance_id: str, local_path: Path, remote_path: str) -> None:
        """Mock copy_to."""
        pass

    def copy_from(self, instance_id: str, remote_path: str, local_path: Path) -> None:
        """Mock copy_from."""
        pass

    def get_logs(self, instance_id: str, tail: int | None = None) -> str:
        """Mock get_logs."""
        return "test logs"

    def get_ssh_config(self, instance_id: str) -> dict[str, Any]:
        """Mock get_ssh_config."""
        return {
            "host": "localhost",
            "port": 2222,
            "username": "vcoding",
        }

    def list_instances(self) -> list[dict[str, Any]]:
        """Mock list_instances."""
        return []


class TestVirtualizationBackend:
    """Tests for VirtualizationBackend abstract base class."""

    def test_init(self) -> None:
        """Test initialization."""
        backend = ConcreteBackend()
        assert backend.config is not None
        assert backend.config.name == "test"

    def test_default_virt_type(self) -> None:
        """Test default virtualization type."""
        backend = ConcreteBackend()
        assert backend.config.virtualization_type == VirtualizationType.DOCKER

    def test_build(self) -> None:
        """Test build method."""
        backend = ConcreteBackend()
        image_id = backend.build()

        assert image_id == "image-123"
        assert backend._built is True

    def test_create(self) -> None:
        """Test create method."""
        backend = ConcreteBackend()
        container_id = backend.create("image-123")

        assert container_id == "container-456"
        assert backend._created is True

    def test_start(self) -> None:
        """Test start method."""
        backend = ConcreteBackend()
        backend.start("container-456")

        assert backend._started is True

    def test_stop(self) -> None:
        """Test stop method."""
        backend = ConcreteBackend()
        backend._started = True
        backend.stop("container-456")

        assert backend._started is False

    def test_destroy(self) -> None:
        """Test destroy method."""
        backend = ConcreteBackend()
        backend._created = True
        backend.destroy("container-456")

        assert backend._created is False

    def test_execute(self) -> None:
        """Test execute method."""
        backend = ConcreteBackend()
        exit_code, stdout, stderr = backend.execute("container-456", "echo hello")

        assert exit_code == 0
        assert stdout == "output"
        assert stderr == ""

    def test_copy_to(self, temp_dir: Path) -> None:
        """Test copy_to method."""
        backend = ConcreteBackend()
        backend.copy_to("container-456", temp_dir, "/remote")
        # Should not raise

    def test_copy_from(self, temp_dir: Path) -> None:
        """Test copy_from method."""
        backend = ConcreteBackend()
        backend.copy_from("container-456", "/remote", temp_dir)
        # Should not raise

    def test_get_logs(self) -> None:
        """Test get_logs method."""
        backend = ConcreteBackend()
        logs = backend.get_logs("container-456")

        assert logs == "test logs"

    def test_get_state(self) -> None:
        """Test get_state method."""
        backend = ConcreteBackend()
        assert backend.get_state("container-456") == ContainerState.NOT_FOUND

        backend._created = True
        assert backend.get_state("container-456") == ContainerState.STOPPED

        backend._started = True
        assert backend.get_state("container-456") == ContainerState.RUNNING

    def test_get_ssh_config(self) -> None:
        """Test get_ssh_config method."""
        backend = ConcreteBackend()
        config = backend.get_ssh_config("container-456")

        assert config["host"] == "localhost"
        assert config["port"] == 2222
        assert config["username"] == "vcoding"

    def test_list_instances(self) -> None:
        """Test list_instances method."""
        backend = ConcreteBackend()
        instances = backend.list_instances()

        assert isinstance(instances, list)
        assert len(instances) == 0

    def test_full_workflow(self) -> None:
        """Test a complete workflow."""
        backend = ConcreteBackend()

        # Build -> Create -> Start -> Execute -> Stop -> Destroy
        image_id = backend.build()
        container_id = backend.create(image_id)
        backend.start(container_id)

        assert backend.get_state(container_id) == ContainerState.RUNNING

        exit_code, stdout, stderr = backend.execute(container_id, "echo test")
        assert exit_code == 0

        backend.stop(container_id)
        assert backend.get_state(container_id) == ContainerState.STOPPED

        backend.destroy(container_id)
