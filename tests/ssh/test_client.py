"""Tests for vcoding.ssh.client module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vcoding.core.types import SshConfig
from vcoding.ssh.client import SSHClient


class TestSSHClient:
    """Tests for SSHClient class."""

    @pytest.fixture
    def ssh_client(self, temp_dir: Path) -> SSHClient:
        """Create SSH client for testing."""
        key_path = temp_dir / "test_key"
        key_path.write_text("fake_key", encoding="utf-8")
        return SSHClient(
            host="localhost",
            port=2222,
            username="testuser",
            private_key_path=key_path,
            timeout=10,
        )

    def test_init(self, ssh_client: SSHClient) -> None:
        """Test initialization."""
        assert ssh_client.host == "localhost"
        assert ssh_client.port == 2222
        assert ssh_client.username == "testuser"

    def test_from_config(self, temp_dir: Path) -> None:
        """Test creating from SSHConfig."""
        config = SshConfig(
            host="192.168.1.1",
            port=22,
            username="admin",
            timeout=60,
        )
        key_path = temp_dir / "key"
        key_path.write_text("key", encoding="utf-8")

        client = SSHClient.from_config(config, key_path)
        assert client.host == "192.168.1.1"
        assert client.port == 22
        assert client.username == "admin"

    def test_build_ssh_command(self, ssh_client: SSHClient) -> None:
        """Test SSH command building."""
        cmd = ssh_client._build_ssh_command("echo hello")

        assert "ssh" in cmd
        assert "-i" in cmd
        assert "-p" in cmd
        assert "2222" in cmd
        assert "testuser@localhost" in cmd
        assert "echo hello" in cmd

    def test_build_ssh_command_with_options(self, ssh_client: SSHClient) -> None:
        """Test SSH command building with extra options."""
        cmd = ssh_client._build_ssh_command("ls", extra_options=["-v", "-A"])

        assert "-v" in cmd
        assert "-A" in cmd

    @patch("subprocess.run")
    def test_execute(self, mock_run: MagicMock, ssh_client: SSHClient) -> None:
        """Test command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        exit_code, stdout, stderr = ssh_client.execute("echo hello")

        assert exit_code == 0
        assert stdout == "output"
        assert stderr == ""

    @patch("subprocess.run")
    def test_execute_with_workdir(
        self, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test command execution with working directory."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        ssh_client.execute("ls", workdir="/app")

        call_args = mock_run.call_args
        command = call_args[0][0]
        # Check that the command includes cd
        assert any("cd /app" in str(arg) for arg in command)

    @patch("subprocess.run")
    def test_execute_with_env(self, mock_run: MagicMock, ssh_client: SSHClient) -> None:
        """Test command execution with environment variables."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        ssh_client.execute("echo $VAR", env={"VAR": "value"})

        call_args = mock_run.call_args
        command = call_args[0][0]
        # Check that the command includes export
        assert any("export" in str(arg) and "VAR" in str(arg) for arg in command)

    @patch("subprocess.run")
    def test_execute_timeout(self, mock_run: MagicMock, ssh_client: SSHClient) -> None:
        """Test command execution timeout handling."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("cmd", 10)

        exit_code, stdout, stderr = ssh_client.execute("long_command")

        assert exit_code == -1
        assert "timed out" in stderr.lower()

    @patch("subprocess.run")
    def test_execute_error(self, mock_run: MagicMock, ssh_client: SSHClient) -> None:
        """Test command execution error handling."""
        mock_run.side_effect = Exception("Connection failed")

        exit_code, stdout, stderr = ssh_client.execute("cmd")

        assert exit_code == -1
        assert "Connection failed" in stderr

    @patch("subprocess.run")
    def test_copy_to(
        self, mock_run: MagicMock, ssh_client: SSHClient, temp_dir: Path
    ) -> None:
        """Test copying files to remote."""
        mock_run.return_value = MagicMock(returncode=0)
        local_file = temp_dir / "local.txt"
        local_file.write_text("content", encoding="utf-8")

        result = ssh_client.copy_to(local_file, "/remote/path")

        assert result is True
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "scp" in call_args

    @patch("subprocess.run")
    def test_copy_to_recursive(
        self, mock_run: MagicMock, ssh_client: SSHClient, temp_dir: Path
    ) -> None:
        """Test copying directory recursively."""
        mock_run.return_value = MagicMock(returncode=0)

        result = ssh_client.copy_to(temp_dir, "/remote/", recursive=True)

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "-r" in call_args

    @patch("subprocess.run")
    def test_copy_from(
        self, mock_run: MagicMock, ssh_client: SSHClient, temp_dir: Path
    ) -> None:
        """Test copying files from remote."""
        mock_run.return_value = MagicMock(returncode=0)

        result = ssh_client.copy_from("/remote/file.txt", temp_dir / "local.txt")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "scp" in call_args

    @patch("subprocess.run")
    def test_copy_failure(
        self, mock_run: MagicMock, ssh_client: SSHClient, temp_dir: Path
    ) -> None:
        """Test copy failure handling."""
        mock_run.return_value = MagicMock(returncode=1)

        result = ssh_client.copy_to(temp_dir / "file", "/remote/")

        assert result is False

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wait_for_connection_success(
        self, mock_sleep: MagicMock, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test waiting for connection success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ok",
            stderr="",
        )

        result = ssh_client.wait_for_connection(max_retries=3)

        assert result is True

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wait_for_connection_retry(
        self, mock_sleep: MagicMock, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test waiting for connection with retries."""
        # Fail twice, then succeed
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="ok", stderr=""),
        ]

        result = ssh_client.wait_for_connection(max_retries=5, retry_interval=0.1)

        assert result is True
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_wait_for_connection_failure(
        self, mock_sleep: MagicMock, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test waiting for connection failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = ssh_client.wait_for_connection(max_retries=3, retry_interval=0.1)

        assert result is False

    @patch("subprocess.run")
    def test_is_connected_true(
        self, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test connection check when connected."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        assert ssh_client.is_connected() is True

    @patch("subprocess.run")
    def test_is_connected_false(
        self, mock_run: MagicMock, ssh_client: SSHClient
    ) -> None:
        """Test connection check when not connected."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        assert ssh_client.is_connected() is False
