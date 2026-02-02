"""CLI for accessing existing vcoding environments.

This module provides command-line interface for:
- Listing running vcoding containers
- Executing commands via SSH
- Copying files to/from containers via SCP
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from vcoding.core.paths import get_workspaces_dir, list_workspaces
from vcoding.ssh.keys import SSHKeyManager


class EnvironmentInfo:
    """Information about a vcoding environment."""

    def __init__(
        self,
        container_id: str,
        container_name: str,
        workspace_name: str,
        status: str,
        ssh_port: int | None,
        workspace_dir: Path | None,
    ) -> None:
        """Initialize environment info.

        Args:
            container_id: Docker container ID.
            container_name: Docker container name.
            workspace_name: vcoding workspace name.
            status: Container status.
            ssh_port: SSH port on host.
            workspace_dir: Path to workspace directory.
        """
        self.container_id = container_id
        self.container_name = container_name
        self.workspace_name = workspace_name
        self.status = status
        self.ssh_port = ssh_port
        self.workspace_dir = workspace_dir

    @property
    def display_name(self) -> str:
        """Get display name for the environment."""
        return f"{self.workspace_name} ({self.status})"

    @property
    def ssh_host(self) -> str:
        """Get SSH host string."""
        return "localhost"

    @property
    def ssh_user(self) -> str:
        """Get SSH username (default vcoding user)."""
        return "vcoding"


def list_environments() -> list[EnvironmentInfo]:
    """List all vcoding environments (running containers).

    Returns:
        List of EnvironmentInfo objects.
    """
    try:
        client = docker.from_env()
    except DockerException:
        return []

    containers = client.containers.list(
        all=True,
        filters={"label": "vcoding.managed=true"},
    )

    # Map workspace names to workspace directories
    workspaces = list_workspaces()
    workspace_map: dict[str, Path] = {}
    for ws in workspaces:
        if ws.get("target_path"):
            workspace_map[ws["target_path"].name] = ws["workspace_dir"]

    environments: list[EnvironmentInfo] = []
    for container in containers:
        workspace_name = container.labels.get("vcoding.workspace", "")

        # Get SSH port
        ssh_port = None
        try:
            container.reload()
            ports = container.ports
            ssh_port_mapping = ports.get("22/tcp", [])
            if ssh_port_mapping:
                ssh_port = int(ssh_port_mapping[0]["HostPort"])
        except Exception:
            pass

        # Find workspace directory
        workspace_dir = workspace_map.get(workspace_name)
        if workspace_dir is None:
            # Try to find by iterating workspaces
            for ws in workspaces:
                config_path = ws["workspace_dir"] / "config.json"
                if config_path.exists():
                    import json

                    try:
                        config = json.loads(config_path.read_text())
                        if config.get("name") == workspace_name:
                            workspace_dir = ws["workspace_dir"]
                            break
                    except Exception:
                        pass

        environments.append(
            EnvironmentInfo(
                container_id=container.id,
                container_name=container.name,
                workspace_name=workspace_name,
                status=container.status,
                ssh_port=ssh_port,
                workspace_dir=workspace_dir,
            )
        )

    return environments


def select_environment(environments: list[EnvironmentInfo]) -> EnvironmentInfo | None:
    """Interactively select an environment.

    Args:
        environments: List of available environments.

    Returns:
        Selected EnvironmentInfo or None if cancelled.
    """
    if not environments:
        print("No vcoding environments found.", file=sys.stderr)
        return None

    if len(environments) == 1:
        return environments[0]

    print("Available vcoding environments:")
    print()
    for i, env in enumerate(environments, 1):
        status_icon = "🟢" if env.status == "running" else "🔴"
        port_info = f"SSH:{env.ssh_port}" if env.ssh_port else "no SSH"
        print(f"  {i}. {status_icon} {env.workspace_name} [{port_info}]")
    print()

    while True:
        try:
            choice = input("Select environment (number or name, q to quit): ").strip()
            if choice.lower() in ("q", "quit", "exit"):
                return None

            # Try as number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(environments):
                    return environments[idx]
            except ValueError:
                pass

            # Try as name
            for env in environments:
                if env.workspace_name == choice or env.container_name == choice:
                    return env

            print(f"Invalid selection: {choice}")
        except (KeyboardInterrupt, EOFError):
            print()
            return None


def get_ssh_key_path(env: EnvironmentInfo) -> Path | None:
    """Get SSH private key path for an environment.

    Args:
        env: Environment info.

    Returns:
        Path to SSH private key or None if not found.
    """
    if env.workspace_dir is None:
        return None

    keys_dir = env.workspace_dir / "keys"
    if not keys_dir.exists():
        return None

    # Try to find the key file
    key_path = keys_dir / f"{env.workspace_name}"
    if key_path.exists():
        return key_path

    # Try with _key suffix
    key_path = keys_dir / f"{env.workspace_name}_key"
    if key_path.exists():
        return key_path

    # Try any .pem file
    for f in keys_dir.iterdir():
        if f.suffix == ".pem" or not f.suffix:
            return f

    return None


def build_ssh_command(
    env: EnvironmentInfo,
    key_path: Path,
    command: str | None = None,
) -> list[str]:
    """Build SSH command for an environment.

    Args:
        env: Environment info.
        key_path: Path to SSH private key.
        command: Optional command to execute.

    Returns:
        SSH command as list of arguments.
    """
    cmd = [
        "ssh",
        "-i",
        str(key_path),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-p",
        str(env.ssh_port),
        f"{env.ssh_user}@{env.ssh_host}",
    ]

    if command:
        cmd.append(command)

    return cmd


def build_scp_command(
    env: EnvironmentInfo,
    key_path: Path,
    local_path: str,
    remote_path: str,
    to_remote: bool = True,
    recursive: bool = False,
) -> list[str]:
    """Build SCP command for an environment.

    Args:
        env: Environment info.
        key_path: Path to SSH private key.
        local_path: Local file path.
        remote_path: Remote file path.
        to_remote: If True, copy to remote. If False, copy from remote.
        recursive: If True, copy recursively.

    Returns:
        SCP command as list of arguments.
    """
    cmd = [
        "scp",
        "-i",
        str(key_path),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-P",
        str(env.ssh_port),
    ]

    if recursive:
        cmd.append("-r")

    remote_spec = f"{env.ssh_user}@{env.ssh_host}:{remote_path}"

    if to_remote:
        cmd.extend([local_path, remote_spec])
    else:
        cmd.extend([remote_spec, local_path])

    return cmd


def cmd_list(args: argparse.Namespace) -> int:
    """List command handler.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code.
    """
    environments = list_environments()

    if not environments:
        print("No vcoding environments found.")
        return 0

    # Filter by status if requested
    if args.running:
        environments = [e for e in environments if e.status == "running"]

    if not environments:
        print("No running vcoding environments found.")
        return 0

    print(f"Found {len(environments)} vcoding environment(s):")
    print()

    for env in environments:
        status_icon = "🟢" if env.status == "running" else "🔴"
        port_info = f"SSH port: {env.ssh_port}" if env.ssh_port else "SSH: N/A"
        print(f"  {status_icon} {env.workspace_name}")
        print(f"     Container: {env.container_name}")
        print(f"     Status: {env.status}")
        print(f"     {port_info}")
        if env.workspace_dir:
            print(f"     Workspace: {env.workspace_dir}")
        print()

    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    """Exec command handler.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code.
    """
    import subprocess

    environments = list_environments()
    running_envs = [e for e in environments if e.status == "running"]

    if not running_envs:
        print("No running vcoding environments found.", file=sys.stderr)
        return 1

    # Select environment
    if args.name:
        env = None
        for e in running_envs:
            if e.workspace_name == args.name or e.container_name == args.name:
                env = e
                break
        if env is None:
            print(f"Environment not found: {args.name}", file=sys.stderr)
            return 1
    else:
        env = select_environment(running_envs)
        if env is None:
            return 1

    # Get SSH key
    key_path = get_ssh_key_path(env)
    if key_path is None:
        print(f"SSH key not found for {env.workspace_name}", file=sys.stderr)
        return 1

    if env.ssh_port is None:
        print(f"SSH port not available for {env.workspace_name}", file=sys.stderr)
        return 1

    # Build and execute command
    command = " ".join(args.command) if args.command else None
    ssh_cmd = build_ssh_command(env, key_path, command)

    if command:
        # Execute command and return
        result = subprocess.run(ssh_cmd)
        return result.returncode
    else:
        # Interactive shell
        import os

        os.execvp("ssh", ssh_cmd)
        return 0  # Never reached


def cmd_cp(args: argparse.Namespace) -> int:
    """Copy command handler.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code.
    """
    import subprocess

    environments = list_environments()
    running_envs = [e for e in environments if e.status == "running"]

    if not running_envs:
        print("No running vcoding environments found.", file=sys.stderr)
        return 1

    # Parse source and destination
    # Format: [env:]path
    # If env: prefix is present, use that environment
    # Otherwise, prompt for selection

    def parse_path(path: str) -> tuple[str | None, str]:
        """Parse path into (env_name, path) tuple."""
        if ":" in path and not path.startswith("/"):
            parts = path.split(":", 1)
            if len(parts) == 2 and not parts[0].startswith("/"):
                return parts[0], parts[1]
        return None, path

    src_env_name, src_path = parse_path(args.source)
    dst_env_name, dst_path = parse_path(args.destination)

    # Determine direction
    if src_env_name and dst_env_name:
        print("Cannot copy between two remote environments.", file=sys.stderr)
        return 1

    if not src_env_name and not dst_env_name:
        print(
            "At least one path must include environment prefix (e.g., myenv:/path).",
            file=sys.stderr,
        )
        return 1

    to_remote = dst_env_name is not None
    env_name = dst_env_name if to_remote else src_env_name
    local_path = src_path if to_remote else dst_path
    remote_path = dst_path if to_remote else src_path

    # Find environment
    env = None
    for e in running_envs:
        if e.workspace_name == env_name or e.container_name == env_name:
            env = e
            break

    if env is None:
        print(f"Environment not found: {env_name}", file=sys.stderr)
        return 1

    # Get SSH key
    key_path = get_ssh_key_path(env)
    if key_path is None:
        print(f"SSH key not found for {env.workspace_name}", file=sys.stderr)
        return 1

    if env.ssh_port is None:
        print(f"SSH port not available for {env.workspace_name}", file=sys.stderr)
        return 1

    # Build and execute SCP command
    scp_cmd = build_scp_command(
        env,
        key_path,
        local_path,
        remote_path,
        to_remote=to_remote,
        recursive=args.recursive,
    )

    result = subprocess.run(scp_cmd)
    return result.returncode


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="vcoding",
        description="Virtualized development environment orchestration tool",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List environments")
    list_parser.add_argument(
        "--running",
        "-r",
        action="store_true",
        help="Show only running environments",
    )
    list_parser.set_defaults(func=cmd_list)

    # exec command
    exec_parser = subparsers.add_parser(
        "exec", aliases=["ssh"], help="Execute command or open SSH shell"
    )
    exec_parser.add_argument(
        "--name",
        "-n",
        help="Environment name (prompts if not specified)",
    )
    exec_parser.add_argument(
        "command",
        nargs="*",
        help="Command to execute (opens interactive shell if not specified)",
    )
    exec_parser.set_defaults(func=cmd_exec)

    # cp command
    cp_parser = subparsers.add_parser("cp", aliases=["copy"], help="Copy files")
    cp_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Copy directories recursively",
    )
    cp_parser.add_argument(
        "source",
        help="Source path (use env:path for remote)",
    )
    cp_parser.add_argument(
        "destination",
        help="Destination path (use env:path for remote)",
    )
    cp_parser.set_defaults(func=cmd_cp)

    return parser


def main() -> int:
    """CLI entry point.

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        # No command specified, show help
        parser.print_help()
        print()
        print("Quick start:")
        print("  vcoding list              # List all environments")
        print("  vcoding exec              # SSH into an environment")
        print("  vcoding exec -n myenv     # SSH into 'myenv'")
        print("  vcoding exec -n myenv ls  # Run 'ls' in 'myenv'")
        print("  vcoding cp file.txt myenv:/workspace/  # Copy to remote")
        print("  vcoding cp myenv:/workspace/file.txt . # Copy from remote")
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
