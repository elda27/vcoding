"""Pytest fixtures and configuration."""

import gc
import shutil
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT
from vcoding.core.types import (
    DockerConfig,
    GitConfig,
    SSHConfig,
    VirtualizationType,
    WorkspaceConfig,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    try:
        yield Path(tmpdir)
    finally:
        # Clean up any git objects that might be holding file locks
        gc.collect()
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors on Windows


@pytest.fixture
def sample_workspace_config(temp_dir: Path) -> WorkspaceConfig:
    """Create a sample workspace configuration."""
    return WorkspaceConfig(
        name="test-workspace",
        host_project_path=temp_dir,
        virtualization_type=VirtualizationType.DOCKER,
        docker=DockerConfig(
            base_image=VCODING_DOCKER_OS_DEFAULT,
            container_name_prefix="vcoding-test",
            ssh_port=22,
            work_dir="/workspace",
            user="vcoding",
        ),
        ssh=SSHConfig(
            host="localhost",
            port=2222,
            username="vcoding",
            timeout=30,
        ),
        git=GitConfig(
            auto_init=True,
            auto_commit=True,
        ),
    )


@pytest.fixture
def mock_docker_client() -> Generator[MagicMock, None, None]:
    """Create a mock Docker client."""
    with patch("docker.from_env") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_ssh_subprocess() -> Generator[MagicMock, None, None]:
    """Mock subprocess for SSH commands."""
    with patch("subprocess.run") as mock:
        mock.return_value = MagicMock(
            returncode=0,
            stdout="ok\n",
            stderr="",
        )
        yield mock
