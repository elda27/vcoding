#!/usr/bin/env python3
"""Template generation example.

This example demonstrates:
- Generating Dockerfile templates for different languages
- Generating .gitignore templates
- Extending existing Dockerfiles with vcoding requirements
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import extend_dockerfile, generate_templates
from vcoding.templates.dockerfile import DockerfileTemplate
from vcoding.templates.gitignore import GitignoreTemplate


def generate_language_templates() -> None:
    """Generate templates for different programming languages."""
    print("=== Supported Languages ===\n")

    languages = ["python", "node", "go", "java", "rust", "ruby"]

    for lang in languages:
        print(f"\n--- {lang.upper()} ---")

        # Generate Dockerfile template
        try:
            df_template = DockerfileTemplate.for_language(lang)
            dockerfile_content = df_template.render()
            print(f"\nDockerfile preview:\n{dockerfile_content[:200]}...")
        except ValueError as e:
            print(f"Dockerfile: {e}")

        # Generate .gitignore template
        try:
            gi_template = GitignoreTemplate.for_language(lang)
            gitignore_content = gi_template.render()
            print(f"\n.gitignore preview:\n{gitignore_content[:150]}...")
        except ValueError as e:
            print(f".gitignore: {e}")


def generate_project_templates() -> None:
    """Generate templates for a new project."""
    project_dir = Path(mkdtemp(prefix="vcoding_templates_"))

    print(f"\n=== Generating templates in {project_dir} ===\n")

    try:
        # Generate templates for a Python project
        generated = generate_templates(
            project_path=project_dir,
            language="python",
            dockerfile=True,
            gitignore=True,
        )

        print("Generated files:")
        for name, path in generated.items():
            print(f"  {name}: {path}")
            print(f"    Content preview: {path.read_text()[:100]}...")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def extend_existing_dockerfile() -> None:
    """Extend an existing Dockerfile with vcoding requirements."""
    project_dir = Path(mkdtemp(prefix="vcoding_extend_"))

    # Create a simple user Dockerfile
    original_dockerfile = project_dir / "Dockerfile"
    original_dockerfile.write_text(
        """FROM python:3.11-slim

# Install project dependencies
RUN pip install flask sqlalchemy

# Copy application code
COPY . /app
WORKDIR /app

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

CMD ["flask", "run", "--host=0.0.0.0"]
"""
    )

    print("=== Original Dockerfile ===")
    print(original_dockerfile.read_text())

    try:
        # Extend Dockerfile with vcoding requirements
        extended_path = extend_dockerfile(
            dockerfile_path=original_dockerfile,
            output_path=project_dir / "Dockerfile.vcoding",
            user="vcoding",
            work_dir="/workspace",
        )

        print("\n=== Extended Dockerfile ===")
        print(extended_path.read_text())

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def custom_dockerfile_template() -> None:
    """Create a custom Dockerfile template."""
    print("\n=== Custom Dockerfile Template ===\n")

    # Create a custom template
    custom_template = DockerfileTemplate(
        base_image="nvidia/cuda:12.0-runtime-ubuntu22.04",
        packages=["python3", "python3-pip", "git", "openssh-server"],
        pip_packages=["torch", "transformers", "numpy"],
        env_vars={"CUDA_VISIBLE_DEVICES": "0"},
        work_dir="/ml-workspace",
    )

    print("Custom ML/CUDA Dockerfile:")
    print(custom_template.render())


def custom_gitignore_template() -> None:
    """Create a custom .gitignore template."""
    print("\n=== Custom .gitignore Template ===\n")

    # Create custom template with additional patterns
    custom_template = GitignoreTemplate(
        patterns=[
            # Python
            "__pycache__/",
            "*.py[cod]",
            "*.egg-info/",
            ".eggs/",
            "dist/",
            "build/",
            # Virtual environments
            "venv/",
            ".venv/",
            "env/",
            # IDE
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            # Project specific
            "data/raw/",
            "models/*.pt",
            "logs/",
            "*.log",
            # Secrets
            ".env",
            ".env.local",
            "secrets/",
            # vcoding
            ".vcoding/",
        ]
    )

    print("Custom .gitignore:")
    print(custom_template.render())


def extend_with_copilot() -> None:
    """Extend Dockerfile with GitHub Copilot CLI."""
    project_dir = Path(mkdtemp(prefix="vcoding_copilot_"))

    # Create a Node.js project Dockerfile
    original_dockerfile = project_dir / "Dockerfile"
    original_dockerfile.write_text(
        """FROM node:20-slim

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

CMD ["npm", "start"]
"""
    )

    print("=== Original Node.js Dockerfile ===")
    print(original_dockerfile.read_text())

    try:
        # Get extended content with SSH and prepare for Copilot
        extended_content = DockerfileTemplate.extend_dockerfile(
            original_dockerfile.read_text(),
            user="developer",
            work_dir="/app",
        )

        # Add GitHub CLI and Copilot extension
        copilot_additions = """
# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \\
    dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \\
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \\
    tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \\
    apt-get update && \\
    apt-get install -y gh && \\
    rm -rf /var/lib/apt/lists/*

# Install GitHub Copilot CLI extension
RUN gh extension install github/gh-copilot || true
"""

        # Insert before ENTRYPOINT if exists, or at end
        final_content = extended_content + copilot_additions

        print("\n=== Extended with Copilot ===")
        print(final_content)

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Template Generation Examples ===\n")

    generate_language_templates()

    print("\n\n")
    generate_project_templates()

    print("\n\n")
    extend_existing_dockerfile()

    print("\n\n")
    custom_dockerfile_template()

    print("\n\n")
    custom_gitignore_template()

    print("\n\n")
    extend_with_copilot()
