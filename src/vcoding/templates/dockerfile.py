"""Dockerfile template generation and extension."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template

from vcoding.core.constant import VCODING_DOCKER_OS_DEFAULT


class DockerfileTemplate:
    """Dockerfile template generator and extender."""

    # Template directory path
    _TEMPLATE_DIR = Path(__file__).parent / "files"

    # Language template file mapping
    LANGUAGE_TEMPLATE_FILES = {
        "python": "Dockerfile.python.j2",
        "nodejs": "Dockerfile.nodejs.j2",
        "go": "Dockerfile.go.j2",
        "rust": "Dockerfile.rust.j2",
        "java": "Dockerfile.java.j2",
    }

    def __init__(
        self,
        base_image: str = "ubuntu:24.04",
        user: str = "vcoding",
        work_dir: str = "/workspace",
    ) -> None:
        """Initialize Dockerfile template.

        Args:
            base_image: Base Docker image.
            user: Username to create in container.
            work_dir: Working directory in container.
        """
        self._base_image = base_image
        self._user = user
        self._work_dir = work_dir
        self._languages: list[str] = []
        self._additional_packages: list[str] = []
        self._custom_commands: list[str] = []
        self._install_claudecode: bool = False

        # Setup Jinja2 environment
        self._env = Environment(
            loader=FileSystemLoader(self._TEMPLATE_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _load_template(self, template_name: str) -> Template:
        """Load a template file.

        Args:
            template_name: Name of the template file.

        Returns:
            Jinja2 Template object.
        """
        return self._env.get_template(template_name)

    def _load_template_string(self, template_name: str) -> str:
        """Load a template file as string.

        Args:
            template_name: Name of the template file.

        Returns:
            Template content as string.
        """
        template_path = self._TEMPLATE_DIR / template_name
        return template_path.read_text(encoding="utf-8")

    def with_language(self, language: str) -> "DockerfileTemplate":
        """Add language support.

        Args:
            language: Language to add (python, nodejs, go, rust, java).

        Returns:
            Self for chaining.
        """
        if language.lower() in self.LANGUAGE_TEMPLATE_FILES:
            self._languages.append(language.lower())
        return self

    def with_packages(self, packages: list[str]) -> "DockerfileTemplate":
        """Add additional apt packages.

        Args:
            packages: List of package names.

        Returns:
            Self for chaining.
        """
        self._additional_packages.extend(packages)
        return self

    def with_command(self, command: str) -> "DockerfileTemplate":
        """Add a custom RUN command.

        Args:
            command: Command to run (without RUN prefix).

        Returns:
            Self for chaining.
        """
        self._custom_commands.append(command)
        return self

    def with_claudecode(self, install: bool = True) -> "DockerfileTemplate":
        """Enable Claude Code CLI installation.

        Args:
            install: Whether to install Claude Code CLI.

        Returns:
            Self for chaining.
        """
        self._install_claudecode = install
        return self

    def _build_language_setup(self) -> str:
        """Build language setup section."""
        if not self._languages:
            return ""

        sections = []
        for lang in self._languages:
            template_file = self.LANGUAGE_TEMPLATE_FILES[lang]
            template = self._load_template(template_file)
            sections.append(template.render(user=self._user))

        return "\n".join(sections)

    def render(self) -> str:
        """Render the Dockerfile.

        Returns:
            Complete Dockerfile content.
        """
        template = self._load_template("Dockerfile.j2")

        return template.render(
            base_image=self._base_image,
            user=self._user,
            work_dir=self._work_dir,
            language_setup=self._build_language_setup(),
            additional_packages=(
                self._additional_packages if self._additional_packages else None
            ),
            custom_commands=self._custom_commands if self._custom_commands else None,
            install_claudecode=self._install_claudecode,
        )

    @classmethod
    def extend_dockerfile(
        cls,
        original_dockerfile: str,
        user: str = "vcoding",
        work_dir: str = "/workspace",
        install_claudecode: bool = False,
    ) -> str:
        """Extend an existing Dockerfile with vcoding requirements.

        Args:
            original_dockerfile: Original Dockerfile content.
            user: Username to create.
            work_dir: Working directory.
            install_claudecode: Whether to install Claude Code CLI.

        Returns:
            Extended Dockerfile content.
        """
        instance = cls(user=user, work_dir=work_dir)
        template = instance._load_template("Dockerfile.extension.j2")

        extension = template.render(
            user=user,
            work_dir=work_dir,
            install_claudecode=install_claudecode,
        )

        return original_dockerfile.rstrip() + "\n" + extension

    @classmethod
    def for_language(
        cls,
        language: str,
        base_image: str | None = None,
        user: str = "vcoding",
        work_dir: str = "/workspace",
        install_claudecode: bool = False,
    ) -> "DockerfileTemplate":
        """Create a template for a specific language.

        Args:
            language: Programming language.
            base_image: Optional base image override.
            user: Username.
            work_dir: Working directory.
            install_claudecode: Whether to install Claude Code CLI.

        Returns:
            Configured DockerfileTemplate.
        """
        # Language-specific base images
        default_images = {
            "python": "python:3.12-slim",
            "nodejs": "node:20-slim",
            "go": "golang:1.22",
            "rust": "rust:latest",
            "java": "eclipse-temurin:17",
        }

        image = base_image or default_images.get(
            language.lower(), VCODING_DOCKER_OS_DEFAULT
        )
        template = cls(base_image=image, user=user, work_dir=work_dir)

        # Don't add language setup if using language-specific base image
        if base_image is None and language.lower() not in default_images:
            template.with_language(language)

        if install_claudecode:
            template.with_claudecode()

        return template
