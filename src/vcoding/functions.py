"""Python API for vcoding.

This module provides high-level functions for interacting with vcoding
as a library.
"""

from pathlib import Path
from typing import Any

from vcoding.agents.base import AgentResult
from vcoding.core.types import WorkspaceConfig
from vcoding.templates.dockerfile import DockerfileTemplate
from vcoding.templates.gitignore import GitignoreTemplate
from vcoding.workspace.git import CommitInfo
from vcoding.workspace.workspace import Workspace


def create_workspace(
    project_path: str | Path,
    name: str | None = None,
    language: str | None = None,
    config: WorkspaceConfig | None = None,
) -> Workspace:
    """Create a new workspace.

    Args:
        project_path: Path to the project directory.
        name: Optional workspace name.
        language: Optional programming language for template generation.
        config: Optional workspace configuration.

    Returns:
        Workspace instance.
    """
    workspace = Workspace(
        project_path=Path(project_path),
        name=name,
        config=config,
    )
    workspace.initialize()

    # Generate templates if language specified
    if language:
        generate_templates(project_path, language)

    return workspace


def start_workspace(project_path: str | Path, name: str | None = None) -> Workspace:
    """Start a workspace's virtual environment.

    Args:
        project_path: Path to the project directory.
        name: Optional workspace name.

    Returns:
        Started Workspace instance.
    """
    workspace = Workspace(project_path=Path(project_path), name=name)
    workspace.start()
    return workspace


def stop_workspace(workspace: Workspace) -> None:
    """Stop a workspace's virtual environment.

    Args:
        workspace: Workspace instance to stop.
    """
    workspace.stop()


def destroy_workspace(workspace: Workspace) -> None:
    """Destroy a workspace and clean up resources.

    Args:
        workspace: Workspace instance to destroy.
    """
    workspace.destroy()
    workspace.cleanup()


def execute_command(
    workspace: Workspace,
    command: str,
    workdir: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> tuple[int, str, str]:
    """Execute a command in the workspace.

    Args:
        workspace: Workspace instance.
        command: Command to execute.
        workdir: Working directory.
        env: Environment variables.
        timeout: Command timeout.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    return workspace.execute(command, workdir=workdir, env=env, timeout=timeout)


def run_agent(
    workspace: Workspace,
    agent_type: str,
    prompt: str,
    workdir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AgentResult:
    """Run a code agent in the workspace.

    Args:
        workspace: Workspace instance.
        agent_type: Type of agent ("copilot" or "claudecode").
        prompt: Prompt for the agent.
        workdir: Working directory.
        options: Agent-specific options.

    Returns:
        AgentResult with execution results.
    """
    return workspace.run_agent(agent_type, prompt, workdir=workdir, options=options)


def sync_to_workspace(
    workspace: Workspace, local_path: str | Path | None = None
) -> None:
    """Sync files to the workspace container.

    Args:
        workspace: Workspace instance.
        local_path: Optional local path. Uses project path if None.
    """
    if local_path:
        workspace.copy_to_container(Path(local_path), workspace.config.docker.work_dir)
    else:
        workspace.sync_to_container()


def sync_from_workspace(
    workspace: Workspace,
    local_path: str | Path | None = None,
) -> None:
    """Sync files from the workspace container.

    Args:
        workspace: Workspace instance.
        local_path: Optional local destination path.
    """
    workspace.sync_from_container(Path(local_path) if local_path else None)


def commit_changes(workspace: Workspace, message: str | None = None) -> str | None:
    """Commit changes in the workspace.

    Args:
        workspace: Workspace instance.
        message: Optional commit message.

    Returns:
        Commit hash if committed, None if no changes.
    """
    return workspace.commit_changes(message)


def rollback(workspace: Workspace, commit_ref: str, hard: bool = False) -> bool:
    """Rollback workspace to a specific commit.

    Args:
        workspace: Workspace instance.
        commit_ref: Commit hash or reference.
        hard: Whether to discard all changes.

    Returns:
        True if successful.
    """
    return workspace.rollback_to(commit_ref, hard=hard)


def get_commits(workspace: Workspace, max_count: int = 50) -> list[CommitInfo]:
    """Get recent commits in the workspace.

    Args:
        workspace: Workspace instance.
        max_count: Maximum number of commits.

    Returns:
        List of CommitInfo.
    """
    return workspace.git.list_commits(max_count)


def generate_templates(
    project_path: str | Path,
    language: str,
    dockerfile: bool = True,
    gitignore: bool = True,
) -> dict[str, Path]:
    """Generate project templates.

    Args:
        project_path: Path to the project directory.
        language: Programming language.
        dockerfile: Whether to generate Dockerfile.
        gitignore: Whether to generate .gitignore.

    Returns:
        Dictionary of generated file paths.
    """
    project_path = Path(project_path)
    generated: dict[str, Path] = {}

    if dockerfile:
        dockerfile_path = project_path / "Dockerfile"
        if not dockerfile_path.exists():
            df_template = DockerfileTemplate.for_language(language)
            dockerfile_path.write_text(df_template.render(), encoding="utf-8")
            generated["dockerfile"] = dockerfile_path

    if gitignore:
        gitignore_path = project_path / ".gitignore"
        if not gitignore_path.exists():
            gi_template = GitignoreTemplate.for_language(language)
            gitignore_path.write_text(gi_template.render(), encoding="utf-8")
            generated["gitignore"] = gitignore_path

    return generated


def extend_dockerfile(
    dockerfile_path: str | Path,
    output_path: str | Path | None = None,
    user: str = "vcoding",
    work_dir: str = "/workspace",
) -> Path:
    """Extend an existing Dockerfile with vcoding requirements.

    Args:
        dockerfile_path: Path to the original Dockerfile.
        output_path: Output path. Overwrites original if None.
        user: Username to create.
        work_dir: Working directory.

    Returns:
        Path to the extended Dockerfile.
    """
    dockerfile_path = Path(dockerfile_path)
    output_path = Path(output_path) if output_path else dockerfile_path

    original_content = dockerfile_path.read_text(encoding="utf-8")
    extended_content = DockerfileTemplate.extend_dockerfile(
        original_content,
        user=user,
        work_dir=work_dir,
    )

    output_path.write_text(extended_content, encoding="utf-8")
    return output_path


# Convenience context manager
class workspace_context:
    """Context manager for workspace lifecycle.

    Example:
        with workspace_context("/path/to/project") as ws:
            ws.execute("echo hello")
    """

    def __init__(
        self,
        project_path: str | Path,
        name: str | None = None,
        auto_destroy: bool = False,
    ) -> None:
        """Initialize workspace context.

        Args:
            project_path: Path to the project directory.
            name: Optional workspace name.
            auto_destroy: Whether to destroy workspace on exit.
        """
        self._project_path = Path(project_path)
        self._name = name
        self._auto_destroy = auto_destroy
        self._workspace: Workspace | None = None

    def __enter__(self) -> Workspace:
        """Start workspace."""
        self._workspace = start_workspace(self._project_path, self._name)
        return self._workspace

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop or destroy workspace."""
        if self._workspace:
            if self._auto_destroy:
                destroy_workspace(self._workspace)
            else:
                stop_workspace(self._workspace)
