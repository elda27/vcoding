"""Tests for vcoding.templates.dockerfile module."""

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT
from vcoding.templates.dockerfile import DockerfileTemplate


class TestDockerfileTemplate:
    """Tests for DockerfileTemplate class."""

    def test_init_defaults(self) -> None:
        """Test default initialization."""
        template = DockerfileTemplate()
        assert template._base_image == VCODING_DOCKER_OS_DEFAULT
        assert template._user == "vcoding"
        assert template._work_dir == "/workspace"

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        template = DockerfileTemplate(
            base_image="alpine:latest",
            user="developer",
            work_dir="/app",
        )
        assert template._base_image == "alpine:latest"
        assert template._user == "developer"
        assert template._work_dir == "/app"

    def test_with_language_chaining(self) -> None:
        """Test method chaining for with_language."""
        template = DockerfileTemplate()
        result = template.with_language("python")
        assert result is template
        assert "python" in template._languages

    def test_with_packages_chaining(self) -> None:
        """Test method chaining for with_packages."""
        template = DockerfileTemplate()
        result = template.with_packages(["vim", "curl"])
        assert result is template
        assert "vim" in template._additional_packages
        assert "curl" in template._additional_packages

    def test_with_command_chaining(self) -> None:
        """Test method chaining for with_command."""
        template = DockerfileTemplate()
        result = template.with_command("echo hello")
        assert result is template
        assert "echo hello" in template._custom_commands

    def test_render_basic(self) -> None:
        """Test basic Dockerfile rendering."""
        template = DockerfileTemplate()
        content = template.render()

        assert f"FROM {VCODING_DOCKER_OS_DEFAULT}" in content
        assert "openssh-server" in content
        assert "EXPOSE 22" in content
        assert "/usr/sbin/sshd" in content
        assert "vcoding" in content  # user

    def test_render_with_python(self) -> None:
        """Test Dockerfile rendering with Python."""
        template = DockerfileTemplate().with_language("python")
        content = template.render()

        assert "python3" in content
        assert "pip" in content

    def test_render_with_nodejs(self) -> None:
        """Test Dockerfile rendering with Node.js."""
        template = DockerfileTemplate().with_language("nodejs")
        content = template.render()

        assert "nodesource" in content or "nodejs" in content

    def test_render_with_go(self) -> None:
        """Test Dockerfile rendering with Go."""
        template = DockerfileTemplate().with_language("go")
        content = template.render()

        assert "go" in content.lower()
        assert "GOPATH" in content

    def test_render_with_rust(self) -> None:
        """Test Dockerfile rendering with Rust."""
        template = DockerfileTemplate().with_language("rust")
        content = template.render()

        assert "rustup" in content

    def test_render_with_java(self) -> None:
        """Test Dockerfile rendering with Java."""
        template = DockerfileTemplate().with_language("java")
        content = template.render()

        assert "openjdk" in content or "java" in content.lower()

    def test_render_with_packages(self) -> None:
        """Test Dockerfile rendering with additional packages."""
        template = DockerfileTemplate().with_packages(["htop", "tree"])
        content = template.render()

        assert "htop" in content
        assert "tree" in content

    def test_render_with_custom_commands(self) -> None:
        """Test Dockerfile rendering with custom commands."""
        template = DockerfileTemplate().with_command("echo 'custom setup'")
        content = template.render()

        assert "echo 'custom setup'" in content

    def test_render_workdir(self) -> None:
        """Test that WORKDIR is set correctly."""
        template = DockerfileTemplate(work_dir="/custom/path")
        content = template.render()

        assert "WORKDIR /custom/path" in content

    def test_render_user_setup(self) -> None:
        """Test user setup in Dockerfile."""
        template = DockerfileTemplate(user="testuser")
        content = template.render()

        assert "useradd" in content
        assert "testuser" in content
        assert "sudoers" in content

    def test_extend_dockerfile(self) -> None:
        """Test extending existing Dockerfile."""
        original = """FROM python:3.12
COPY . /app
RUN pip install -r requirements.txt
"""
        extended = DockerfileTemplate.extend_dockerfile(
            original,
            user="appuser",
            work_dir="/app",
        )

        assert "FROM python:3.12" in extended
        assert "openssh-server" in extended
        assert "appuser" in extended
        assert "vcoding extensions" in extended

    def test_for_language_python(self) -> None:
        """Test creating template for Python."""
        template = DockerfileTemplate.for_language("python")
        content = template.render()

        assert "python" in content.lower()

    def test_for_language_nodejs(self) -> None:
        """Test creating template for Node.js."""
        template = DockerfileTemplate.for_language("nodejs")
        content = template.render()

        assert "node" in content.lower()

    def test_for_language_with_custom_base(self) -> None:
        """Test creating template with custom base image."""
        template = DockerfileTemplate.for_language("python", base_image="ubuntu:24.04")
        content = template.render()

        assert "FROM ubuntu:24.04" in content

    def test_ssh_configuration(self) -> None:
        """Test SSH server configuration in Dockerfile."""
        template = DockerfileTemplate()
        content = template.render()

        assert "PermitRootLogin no" in content
        assert "PasswordAuthentication no" in content
        assert "PubkeyAuthentication yes" in content
        assert "mkdir -p /var/run/sshd" in content

    def test_multiple_languages(self) -> None:
        """Test adding multiple languages."""
        template = DockerfileTemplate()
        template.with_language("python").with_language("nodejs")
        content = template.render()

        assert "python" in content.lower()
        assert "node" in content.lower()

    def test_unknown_language_ignored(self) -> None:
        """Test that unknown languages are ignored."""
        template = DockerfileTemplate()
        template.with_language("unknown_lang")
        assert "unknown_lang" not in template._languages
