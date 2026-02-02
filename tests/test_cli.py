"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import MagicMock, patch


from vcoding.cli import (
    EnvironmentInfo,
    build_scp_command,
    build_ssh_command,
    create_parser,
    list_environments,
)


class TestEnvironmentInfo:
    """Tests for EnvironmentInfo class."""

    def test_environment_info_properties(self) -> None:
        """Test EnvironmentInfo properties."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )

        assert env.container_id == "abc123"
        assert env.container_name == "vcoding-test"
        assert env.workspace_name == "test"
        assert env.status == "running"
        assert env.ssh_port == 2222
        assert env.workspace_dir == Path("/tmp/workspace")
        assert env.display_name == "test (running)"
        assert env.ssh_host == "localhost"
        assert env.ssh_user == "vcoding"


class TestBuildSshCommand:
    """Tests for build_ssh_command function."""

    def test_build_ssh_command_no_command(self) -> None:
        """Test building SSH command without remote command."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )
        key_path = Path("/tmp/key")

        cmd = build_ssh_command(env, key_path)

        assert cmd[0] == "ssh"
        assert "-i" in cmd
        assert str(key_path) in cmd
        assert "-p" in cmd
        assert "2222" in cmd
        assert "vcoding@localhost" in cmd

    def test_build_ssh_command_with_command(self) -> None:
        """Test building SSH command with remote command."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )
        key_path = Path("/tmp/key")

        cmd = build_ssh_command(env, key_path, "ls -la")

        assert cmd[-1] == "ls -la"


class TestBuildScpCommand:
    """Tests for build_scp_command function."""

    def test_build_scp_command_to_remote(self) -> None:
        """Test building SCP command for upload."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )
        key_path = Path("/tmp/key")

        cmd = build_scp_command(
            env, key_path, "/local/file.txt", "/remote/file.txt", to_remote=True
        )

        assert cmd[0] == "scp"
        assert "-i" in cmd
        assert str(key_path) in cmd
        assert "-P" in cmd
        assert "2222" in cmd
        assert "/local/file.txt" in cmd
        assert "vcoding@localhost:/remote/file.txt" in cmd

    def test_build_scp_command_from_remote(self) -> None:
        """Test building SCP command for download."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )
        key_path = Path("/tmp/key")

        cmd = build_scp_command(
            env, key_path, "/local/file.txt", "/remote/file.txt", to_remote=False
        )

        assert "vcoding@localhost:/remote/file.txt" in cmd
        assert cmd[-1] == "/local/file.txt"

    def test_build_scp_command_recursive(self) -> None:
        """Test building SCP command with recursive flag."""
        env = EnvironmentInfo(
            container_id="abc123",
            container_name="vcoding-test",
            workspace_name="test",
            status="running",
            ssh_port=2222,
            workspace_dir=Path("/tmp/workspace"),
        )
        key_path = Path("/tmp/key")

        cmd = build_scp_command(
            env, key_path, "/local/dir", "/remote/dir", to_remote=True, recursive=True
        )

        assert "-r" in cmd


class TestCreateParser:
    """Tests for CLI argument parser."""

    def test_list_command(self) -> None:
        """Test parsing list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])

        assert args.command == "list"
        assert not args.running

    def test_list_running(self) -> None:
        """Test parsing list --running command."""
        parser = create_parser()
        args = parser.parse_args(["list", "--running"])

        assert args.command == "list"
        assert args.running

    def test_exec_command_interactive(self) -> None:
        """Test parsing exec command without remote command."""
        parser = create_parser()
        args = parser.parse_args(["exec"])

        assert args.command == "exec"
        assert args.command == "exec"
        assert args.name is None

    def test_exec_command_with_name(self) -> None:
        """Test parsing exec command with name."""
        parser = create_parser()
        args = parser.parse_args(["exec", "-n", "myenv"])

        assert args.name == "myenv"

    def test_exec_command_with_remote_command(self) -> None:
        """Test parsing exec command with remote command."""
        parser = create_parser()
        args = parser.parse_args(["exec", "-n", "myenv", "ls", "-la"])

        assert args.name == "myenv"
        assert args.command == ["ls", "-la"]

    def test_cp_command(self) -> None:
        """Test parsing cp command."""
        parser = create_parser()
        args = parser.parse_args(["cp", "local.txt", "myenv:/remote.txt"])

        assert args.command == "cp"
        assert args.source == "local.txt"
        assert args.destination == "myenv:/remote.txt"
        assert not args.recursive

    def test_cp_command_recursive(self) -> None:
        """Test parsing cp command with recursive flag."""
        parser = create_parser()
        args = parser.parse_args(["cp", "-r", "local_dir", "myenv:/remote_dir"])

        assert args.recursive
        assert args.source == "local_dir"
        assert args.destination == "myenv:/remote_dir"


class TestListEnvironments:
    """Tests for list_environments function."""

    @patch("vcoding.cli.docker.from_env")
    @patch("vcoding.cli.list_workspaces")
    def test_list_environments_no_docker(
        self, mock_list_workspaces: MagicMock, mock_docker: MagicMock
    ) -> None:
        """Test list_environments when Docker is not available."""
        from docker.errors import DockerException

        mock_docker.side_effect = DockerException("Docker not available")

        result = list_environments()

        assert result == []

    @patch("vcoding.cli.docker.from_env")
    @patch("vcoding.cli.list_workspaces")
    def test_list_environments_with_containers(
        self, mock_list_workspaces: MagicMock, mock_docker: MagicMock
    ) -> None:
        """Test list_environments with running containers."""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client

        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "vcoding-test"
        mock_container.labels = {"vcoding.workspace": "test"}
        mock_container.status = "running"
        mock_container.ports = {"22/tcp": [{"HostPort": "2222"}]}

        mock_client.containers.list.return_value = [mock_container]
        mock_list_workspaces.return_value = []

        result = list_environments()

        assert len(result) == 1
        assert result[0].container_id == "abc123"
        assert result[0].workspace_name == "test"
        assert result[0].status == "running"
        assert result[0].ssh_port == 2222
