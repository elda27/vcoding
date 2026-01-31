"""Docker virtualization backend."""

import io
import tarfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

from vcoding.core.types import ContainerState, WorkspaceConfig
from vcoding.virtualization.base import VirtualizationBackend


class DockerNotAvailableError(Exception):
    """Raised when Docker is not available or not running."""

    pass


class DockerBackend(VirtualizationBackend):
    """Docker-based virtualization backend."""

    def __init__(self, config: WorkspaceConfig) -> None:
        """Initialize Docker backend.

        Args:
            config: Workspace configuration.

        Raises:
            DockerNotAvailableError: If Docker is not available or not running.
        """
        super().__init__(config)
        try:
            self._client = docker.from_env()
        except DockerException as e:
            raise DockerNotAvailableError(
                "Docker is not available. Please ensure Docker Desktop is running.\n"
                f"Original error: {e}"
            ) from e
        self._api = self._client.api

    @property
    def container_name(self) -> str:
        """Get the container name for this workspace."""
        return f"{self._config.docker.container_name_prefix}-{self._config.name}"

    def _get_container(self, instance_id: str) -> Container | None:
        """Get container by ID or name.

        Args:
            instance_id: Container ID or name.

        Returns:
            Container object or None if not found.
        """
        try:
            return self._client.containers.get(instance_id)
        except NotFound:
            return None

    def build(self, dockerfile_content: str | None = None) -> str:
        """Build Docker image.

        Args:
            dockerfile_content: Optional Dockerfile content.

        Returns:
            Image ID.
        """
        if dockerfile_content is None:
            if self._config.docker.dockerfile_path:
                dockerfile_content = self._config.docker.dockerfile_path.read_text(
                    encoding="utf-8"
                )
            else:
                dockerfile_content = self._generate_default_dockerfile()

        # Build image from Dockerfile content
        image_tag = f"vcoding/{self._config.name}:latest"

        # Create a tar archive with Dockerfile
        dockerfile_bytes = dockerfile_content.encode("utf-8")
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            dockerfile_info = tarfile.TarInfo(name="Dockerfile")
            dockerfile_info.size = len(dockerfile_bytes)
            tar.addfile(dockerfile_info, io.BytesIO(dockerfile_bytes))
        tar_buffer.seek(0)

        # Build the image
        image, logs = self._client.images.build(
            fileobj=tar_buffer,
            custom_context=True,
            tag=image_tag,
            rm=True,
        )

        if image.id is None:
            raise RuntimeError("Failed to build Docker image.")

        return image.id

    def _generate_default_dockerfile(self) -> str:
        """Generate default Dockerfile with SSH support.

        Returns:
            Dockerfile content.
        """
        from vcoding.templates.dockerfile import DockerfileTemplate

        user = self._config.docker.user
        work_dir = self._config.docker.work_dir
        base_image = self._config.docker.base_image

        template = DockerfileTemplate(
            base_image=base_image,
            user=user,
            work_dir=work_dir,
        )

        # Add language support if specified
        if self._config.language:
            template.with_language(self._config.language)

        return template.render()

    def create(self, image: str | None = None) -> str:
        """Create a new Docker container.

        Args:
            image: Optional image to use.

        Returns:
            Container ID.
        """
        if image is None:
            image = self.build()

        # Remove existing container with same name if it exists
        existing_container = self._get_container(self.container_name)
        if existing_container:
            try:
                existing_container.stop(timeout=5)
            except Exception:
                pass
            try:
                existing_container.remove(force=True)
            except docker.errors.APIError as e:
                # Container might be auto-removing, wait for it to finish
                if "removal" in str(e).lower() or "in progress" in str(e).lower():
                    import time

                    for _ in range(10):
                        time.sleep(0.5)
                        if self._get_container(self.container_name) is None:
                            break
                else:
                    raise

        # Find available port
        import socket

        def find_free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                return s.getsockname()[1]

        host_port = find_free_port()

        # Per SPEC.md 7.1: Do not mount host directories directly
        # File transfer is done via Docker API (put_archive/get_archive)
        # Authentication is handled via environment variables

        # Prepare environment variables
        environment = self._get_auth_environment()

        container = self._client.containers.create(
            image=image,
            name=self.container_name,
            detach=True,
            auto_remove=True,
            ports={"22/tcp": host_port},
            environment=environment,
            labels={
                "vcoding.workspace": self._config.name,
                "vcoding.managed": "true",
            },
        )

        return container.id

    def _get_auth_environment(self) -> dict[str, str]:
        """Get authentication environment variables to pass to container.

        Checks for GitHub tokens in the host environment, or tries to get
        token from gh CLI if authenticated.

        Returns:
            Dictionary of environment variables.
        """
        import os
        import subprocess

        env = {}

        # Check for GitHub tokens (in order of precedence for Copilot CLI)
        token_found = False
        for token_name in ["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"]:
            token = os.environ.get(token_name)
            if token:
                env[token_name] = token
                token_found = True
                break  # Only pass the first one found

        # If no token in environment, try to get from gh CLI
        if not token_found:
            gh_token = self._get_gh_auth_token()
            if gh_token:
                env["GH_TOKEN"] = gh_token

        # Also pass ANTHROPIC_API_KEY for Claude Code
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            env["ANTHROPIC_API_KEY"] = anthropic_key

        return env

    def _get_gh_auth_token(self) -> str | None:
        """Get GitHub token from gh CLI authentication.

        This runs `gh auth token` on the host to retrieve the token
        that was set via `gh auth login`.

        Returns:
            GitHub token string, or None if not authenticated.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # gh CLI not installed or not working
            pass

        return None

    def start(self, instance_id: str) -> None:
        """Start a Docker container.

        Args:
            instance_id: Container ID.
        """
        container = self._get_container(instance_id)
        if container:
            container.start()

    def stop(self, instance_id: str, timeout: int = 10) -> None:
        """Stop a Docker container.

        Args:
            instance_id: Container ID.
            timeout: Timeout in seconds.
        """
        container = self._get_container(instance_id)
        if container:
            container.stop(timeout=timeout)

    def destroy(self, instance_id: str) -> None:
        """Destroy a Docker container.

        Args:
            instance_id: Container ID.
        """
        container = self._get_container(instance_id)
        if container:
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            container.remove(force=True)

    def get_state(self, instance_id: str) -> ContainerState:
        """Get container state.

        Args:
            instance_id: Container ID.

        Returns:
            Container state.
        """
        container = self._get_container(instance_id)
        if container is None:
            return ContainerState.NOT_FOUND

        status = container.status
        if status == "running":
            return ContainerState.RUNNING
        elif status == "paused":
            return ContainerState.PAUSED
        elif status in ("created", "exited", "dead"):
            return ContainerState.STOPPED
        else:
            return ContainerState.ERROR

    def execute(
        self,
        instance_id: str,
        command: str | list[str],
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Execute command in container.

        Args:
            instance_id: Container ID.
            command: Command to execute.
            workdir: Working directory.
            env: Environment variables.
            timeout: Command timeout.

        Returns:
            Tuple of (exit_code, stdout, stderr).
        """
        container = self._get_container(instance_id)
        if container is None:
            return (-1, "", "Container not found")

        if isinstance(command, str):
            cmd = ["/bin/bash", "-c", command]
        else:
            cmd = command

        result = container.exec_run(
            cmd,
            workdir=workdir or self._config.docker.work_dir,
            environment=env,
            demux=True,
            user=self._config.docker.user,
        )

        stdout = result.output[0].decode("utf-8") if result.output[0] else ""
        stderr = result.output[1].decode("utf-8") if result.output[1] else ""

        return (result.exit_code, stdout, stderr)

    def copy_to(
        self,
        instance_id: str,
        local_path: Path,
        remote_path: str,
        flatten: bool = False,
    ) -> None:
        """Copy files to container.

        Args:
            instance_id: Container ID.
            local_path: Local path.
            remote_path: Remote path.
            flatten: If True and local_path is a directory, copy contents directly
                    to remote_path instead of creating a subdirectory.
        """
        container = self._get_container(instance_id)
        if container is None:
            raise ValueError(f"Container {instance_id} not found")

        # Create tar archive
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            if flatten and local_path.is_dir():
                # Copy directory contents directly (without creating subdirectory)
                for item in local_path.iterdir():
                    tar.add(item, arcname=item.name)
            else:
                tar.add(local_path, arcname=Path(local_path).name)
        tar_buffer.seek(0)

        container.put_archive(remote_path, tar_buffer)

    def copy_from(
        self,
        instance_id: str,
        remote_path: str,
        local_path: Path,
        flatten: bool = False,
    ) -> None:
        """Copy files from container.

        Args:
            instance_id: Container ID.
            remote_path: Remote path.
            local_path: Local path.
            flatten: If True and remote_path is a directory, extract contents
                    directly to local_path instead of creating a subdirectory.
        """
        container = self._get_container(instance_id)
        if container is None:
            raise ValueError(f"Container {instance_id} not found")

        bits, stat = container.get_archive(remote_path)

        # Extract tar archive
        tar_buffer = io.BytesIO()
        for chunk in bits:
            tar_buffer.write(chunk)
        tar_buffer.seek(0)

        # Ensure local_path exists
        local_path.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
            if flatten:
                # Extract without the top-level directory
                remote_basename = Path(remote_path).name
                for member in tar.getmembers():
                    # Strip the leading directory name
                    if member.name == remote_basename:
                        continue  # Skip the directory itself
                    if member.name.startswith(remote_basename + "/"):
                        member.name = member.name[len(remote_basename) + 1 :]
                        if member.name:  # Don't extract empty names
                            self._safe_extract_member(tar, member, local_path)
                    else:
                        self._safe_extract_member(tar, member, local_path)
            else:
                # Use filter='data' for safe extraction
                tar.extractall(local_path, filter="data")

    def _safe_extract_member(
        self, tar: tarfile.TarFile, member: tarfile.TarInfo, path: Path
    ) -> None:
        """Safely extract a tar member, handling Windows permissions.

        Args:
            tar: The tar file.
            member: The member to extract.
            path: Destination path.
        """
        target_path = path / member.name

        # Skip .git directory contents on Windows to avoid permission issues
        # The git repository will be re-initialized locally if needed
        if ".git" in member.name.split("/") or ".git" in member.name.split("\\"):
            return

        try:
            if member.isdir():
                target_path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                # Ensure parent directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Remove existing file if it exists (Windows compat)
                if target_path.exists():
                    target_path.unlink()

                # Extract file content
                with tar.extractfile(member) as src:
                    if src:
                        target_path.write_bytes(src.read())
            elif member.issym():
                # Handle symlinks - on Windows, skip or create as file
                pass
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not extract {member.name}: {e}")

    def get_ssh_config(self, instance_id: str) -> dict[str, Any]:
        """Get SSH configuration for container.

        Args:
            instance_id: Container ID.

        Returns:
            SSH configuration dictionary.
        """
        container = self._get_container(instance_id)
        if container is None:
            raise ValueError(f"Container {instance_id} not found")

        # Get port mapping
        container.reload()
        ports = container.ports
        ssh_port_mapping = ports.get("22/tcp", [])
        if ssh_port_mapping:
            host_port = int(ssh_port_mapping[0]["HostPort"])
        else:
            host_port = 22

        return {
            "host": "localhost",
            "port": host_port,
            "username": self._config.docker.user,
        }

    def get_logs(self, instance_id: str, tail: int | None = None) -> str:
        """Get container logs.

        Args:
            instance_id: Container ID.
            tail: Number of lines from end.

        Returns:
            Log output.
        """
        container = self._get_container(instance_id)
        if container is None:
            return ""

        logs = container.logs(tail=tail if tail else "all")
        return logs.decode("utf-8")

    def list_instances(self) -> list[dict[str, Any]]:
        """List all vcoding containers.

        Returns:
            List of container information.
        """
        containers = self._client.containers.list(
            all=True,
            filters={"label": "vcoding.managed=true"},
        )

        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "workspace": c.labels.get("vcoding.workspace", ""),
            }
            for c in containers
        ]

    def inject_ssh_key(self, instance_id: str, public_key: str) -> None:
        """Inject SSH public key into container.

        Args:
            instance_id: Container ID.
            public_key: SSH public key content.
        """
        container = self._get_container(instance_id)
        if container is None:
            raise ValueError(f"Container {instance_id} not found")

        user = self._config.docker.user
        ssh_dir = f"/home/{user}/.ssh"

        # Create authorized_keys file
        self.execute(
            instance_id,
            f"mkdir -p {ssh_dir} && chmod 700 {ssh_dir}",
        )

        # Write public key
        escaped_key = public_key.replace('"', '\\"')
        self.execute(
            instance_id,
            f'echo "{escaped_key}" > {ssh_dir}/authorized_keys && chmod 600 {ssh_dir}/authorized_keys && chown -R {user}:{user} {ssh_dir}',
        )
