"""SSH client for remote command execution."""

import subprocess
import time
from pathlib import Path

from vcoding.core.types import SSHConfig


class SSHClient:
    """SSH client for executing commands on remote hosts."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        private_key_path: Path,
        timeout: int = 30,
    ) -> None:
        """Initialize SSH client.

        Args:
            host: Remote host address.
            port: SSH port.
            username: SSH username.
            private_key_path: Path to private key file.
            timeout: Connection timeout in seconds.
        """
        self._host = host
        self._port = port
        self._username = username
        self._private_key_path = private_key_path
        self._timeout = timeout

    @classmethod
    def from_config(cls, config: SSHConfig, private_key_path: Path) -> "SSHClient":
        """Create SSH client from configuration.

        Args:
            config: SSH configuration.
            private_key_path: Path to private key file.

        Returns:
            SSHClient instance.
        """
        return cls(
            host=config.host,
            port=config.port,
            username=config.username,
            private_key_path=private_key_path,
            timeout=config.timeout,
        )

    @property
    def host(self) -> str:
        """Get remote host."""
        return self._host

    @property
    def port(self) -> int:
        """Get SSH port."""
        return self._port

    @property
    def username(self) -> str:
        """Get SSH username."""
        return self._username

    def _build_ssh_command(
        self,
        command: str | None = None,
        extra_options: list[str] | None = None,
    ) -> list[str]:
        """Build SSH command line.

        Args:
            command: Remote command to execute.
            extra_options: Additional SSH options.

        Returns:
            Command line as list.
        """
        cmd = [
            "ssh",
            "-i",
            str(self._private_key_path),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={self._timeout}",
            "-o",
            "BatchMode=yes",
            "-p",
            str(self._port),
        ]

        if extra_options:
            cmd.extend(extra_options)

        cmd.append(f"{self._username}@{self._host}")

        if command:
            cmd.append(command)

        return cmd

    def execute(
        self,
        command: str,
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command on the remote host.

        Args:
            command: Command to execute.
            workdir: Working directory for the command.
            env: Environment variables.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        # Build command with environment and workdir
        full_command = ""

        if env:
            env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
            full_command += f"export {env_str}; "

        if workdir:
            full_command += f"cd {workdir} && "

        full_command += command

        ssh_cmd = self._build_ssh_command(full_command)

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                timeout=timeout or self._timeout,
                text=True,
            )
            return (result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return (-1, "", "Command timed out")
        except Exception as e:
            return (-1, "", str(e))

    def execute_interactive(
        self,
        command: str,
        input_data: str | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute an interactive command.

        Args:
            command: Command to execute.
            input_data: Input to send to the command.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        ssh_cmd = self._build_ssh_command(command, ["-t", "-t"])

        try:
            result = subprocess.run(
                ssh_cmd,
                input=input_data,
                capture_output=True,
                timeout=timeout or self._timeout,
                text=True,
            )
            return (result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return (-1, "", "Command timed out")
        except Exception as e:
            return (-1, "", str(e))

    def copy_to(
        self,
        local_path: Path,
        remote_path: str,
        recursive: bool = False,
    ) -> bool:
        """Copy file or directory to remote host using SCP.

        Args:
            local_path: Local file or directory path.
            remote_path: Remote destination path.
            recursive: Whether to copy recursively (for directories).

        Returns:
            True if successful, False otherwise.
        """
        cmd = [
            "scp",
            "-i",
            str(self._private_key_path),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-P",
            str(self._port),
        ]

        if recursive:
            cmd.append("-r")

        cmd.extend(
            [
                str(local_path),
                f"{self._username}@{self._host}:{remote_path}",
            ]
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self._timeout * 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def copy_from(
        self,
        remote_path: str,
        local_path: Path,
        recursive: bool = False,
    ) -> bool:
        """Copy file or directory from remote host using SCP.

        Args:
            remote_path: Remote file or directory path.
            local_path: Local destination path.
            recursive: Whether to copy recursively (for directories).

        Returns:
            True if successful, False otherwise.
        """
        cmd = [
            "scp",
            "-i",
            str(self._private_key_path),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-P",
            str(self._port),
        ]

        if recursive:
            cmd.append("-r")

        cmd.extend(
            [
                f"{self._username}@{self._host}:{remote_path}",
                str(local_path),
            ]
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self._timeout * 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def wait_for_connection(
        self,
        max_retries: int = 30,
        retry_interval: float = 1.0,
    ) -> bool:
        """Wait for SSH connection to become available.

        Args:
            max_retries: Maximum number of retries.
            retry_interval: Interval between retries in seconds.

        Returns:
            True if connection successful, False otherwise.
        """
        for _ in range(max_retries):
            exit_code, _, _ = self.execute("echo ok", timeout=5)
            if exit_code == 0:
                return True
            time.sleep(retry_interval)
        return False

    def is_connected(self) -> bool:
        """Check if SSH connection is available.

        Returns:
            True if connected, False otherwise.
        """
        exit_code, _, _ = self.execute("echo ok", timeout=5)
        return exit_code == 0
