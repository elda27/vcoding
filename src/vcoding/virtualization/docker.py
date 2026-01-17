"""Docker virtualization backend."""

import io
import tarfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import NotFound
from docker.models.containers import Container

from vcoding.core.types import ContainerState, WorkspaceConfig
from vcoding.virtualization.base import VirtualizationBackend


class DockerBackend(VirtualizationBackend):
    """Docker-based virtualization backend."""

    def __init__(self, config: WorkspaceConfig) -> None:
        """Initialize Docker backend.

        Args:
            config: Workspace configuration.
        """
        super().__init__(config)
        self._client = docker.from_env()
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
        user = self._config.docker.user
        work_dir = self._config.docker.work_dir

        return f"""FROM {self._config.docker.base_image}

# Install SSH server and basic tools
RUN apt-get update && apt-get install -y \\
    openssh-server \\
    sudo \\
    git \\
    curl \\
    wget \\
    vim \\
    && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir /var/run/sshd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
RUN sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Create user
RUN useradd -m -s /bin/bash {user} && \\
    echo "{user} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup SSH directory
RUN mkdir -p /home/{user}/.ssh && \\
    chmod 700 /home/{user}/.ssh && \\
    chown -R {user}:{user} /home/{user}/.ssh

# Create workspace directory
RUN mkdir -p {work_dir} && \\
    chown -R {user}:{user} {work_dir}

WORKDIR {work_dir}

# Expose SSH port
EXPOSE 22

# Start SSH server
CMD ["/usr/sbin/sshd", "-D"]
"""

    def create(self, image: str | None = None) -> str:
        """Create a new Docker container.

        Args:
            image: Optional image to use.

        Returns:
            Container ID.
        """
        if image is None:
            image = self.build()

        # Find available port
        import socket

        def find_free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                return s.getsockname()[1]

        host_port = find_free_port()

        container = self._client.containers.create(
            image=image,
            name=self.container_name,
            detach=True,
            ports={"22/tcp": host_port},
            volumes={
                str(self._config.temp_dir): {
                    "bind": "/vcoding_temp",
                    "mode": "rw",
                }
            },
            labels={
                "vcoding.workspace": self._config.name,
                "vcoding.managed": "true",
            },
        )

        return container.id

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
    ) -> None:
        """Copy files to container.

        Args:
            instance_id: Container ID.
            local_path: Local path.
            remote_path: Remote path.
        """
        container = self._get_container(instance_id)
        if container is None:
            raise ValueError(f"Container {instance_id} not found")

        # Create tar archive
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(local_path, arcname=Path(local_path).name)
        tar_buffer.seek(0)

        container.put_archive(remote_path, tar_buffer)

    def copy_from(
        self,
        instance_id: str,
        remote_path: str,
        local_path: Path,
    ) -> None:
        """Copy files from container.

        Args:
            instance_id: Container ID.
            remote_path: Remote path.
            local_path: Local path.
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

        with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
            tar.extractall(local_path)

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
