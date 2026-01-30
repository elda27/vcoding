"""Python API for vcoding.

This module provides high-level functions for interacting with vcoding
as a library.
"""

from pathlib import Path
from typing import Any

from vcoding.agents.base import AgentResult
from vcoding.core.paths import (
    cleanup_orphaned_workspaces,
    find_orphaned_workspaces,
    get_app_data_dir,
    list_workspaces,
)
from vcoding.core.types import WorkspaceConfig
from vcoding.templates.dockerfile import DockerfileTemplate
from vcoding.templates.gitignore import GitignoreTemplate
from vcoding.workspace.git import CommitInfo
from vcoding.workspace.workspace import Workspace


def create_workspace(
    target: str | Path,
    name: str | None = None,
    language: str | None = None,
    config: WorkspaceConfig | None = None,
) -> Workspace:
    """Create a new workspace.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.
        language: Optional programming language for template generation.
        config: Optional workspace configuration.

    Returns:
        Workspace instance.
    """
    target_path = Path(target)
    workspace = Workspace(
        target=target_path,
        name=name,
        config=config,
    )
    workspace.initialize()

    # Generate templates if language specified and target is a directory
    if language and target_path.is_dir():
        generate_templates(target_path, language)

    return workspace


def start_workspace(target: str | Path, name: str | None = None) -> Workspace:
    """Start a workspace's virtual environment.

    Args:
        target: Path to the target file or directory.
        name: Optional workspace name.

    Returns:
        Started Workspace instance.
    """
    workspace = Workspace(target=Path(target), name=name)
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

    Automatically handles start/stop and file syncing.

    Example:
        with workspace_context("/path/to/project") as ws:
            ws.generate("Create a hello function", output="hello.py")
            ws.run("python hello.py")
    """

    def __init__(
        self,
        target: str | Path,
        name: str | None = None,
        language: str | None = None,
        auto_sync: bool = True,
        auto_destroy: bool = False,
    ) -> None:
        """Initialize workspace context.

        Args:
            target: Path to the target file or directory.
            name: Optional workspace name.
            language: Optional language for template generation.
            auto_sync: Whether to auto-sync files on enter/exit.
            auto_destroy: Whether to destroy workspace on exit.
        """
        self._target = Path(target)
        self._name = name
        self._language = language
        self._auto_sync = auto_sync
        self._auto_destroy = auto_destroy
        self._workspace: Workspace | None = None

    def __enter__(self) -> Workspace:
        """Start workspace and sync files."""
        self._workspace = create_workspace(
            self._target,
            name=self._name,
            language=self._language,
        )
        self._workspace.start()
        if self._auto_sync:
            self._workspace.sync_to_container()
        return self._workspace

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sync files and stop/destroy workspace."""
        if self._workspace:
            if self._auto_sync and exc_type is None:
                self._workspace.sync_from_container()
            if self._auto_destroy:
                destroy_workspace(self._workspace)
            else:
                stop_workspace(self._workspace)


# Workspace management utilities
def get_vcoding_data_dir() -> Path:
    """Get the vcoding application data directory.

    Returns:
        Path to the application data directory.
    """
    return get_app_data_dir()


def list_all_workspaces() -> list[dict[str, Any]]:
    """List all workspaces.

    Returns:
        List of workspace information dictionaries.
    """
    return list_workspaces()


def find_orphaned() -> list[Path]:
    """Find workspaces whose target paths no longer exist.

    Returns:
        List of orphaned workspace directories.
    """
    return find_orphaned_workspaces()


def cleanup_orphaned() -> int:
    """Remove orphaned workspaces.

    Returns:
        Number of removed workspaces.
    """
    return cleanup_orphaned_workspaces()


# =============================================================================
# One-shot convenience functions (no manual lifecycle management needed)
# =============================================================================


def generate(
    target: str | Path,
    prompt: str,
    output: str | None = None,
    agent: str = "copilot",
    language: str | None = None,
) -> AgentResult:
    """Generate code in a single call (one-shot API).

    This function handles the entire lifecycle: workspace creation,
    container start, file sync, agent execution, and cleanup.

    Args:
        target: Path to the project directory.
        prompt: What to generate (e.g., "Create a fibonacci function").
        output: Output file path relative to project (e.g., "fibonacci.py").
        agent: Agent to use ("copilot" or "claudecode").
        language: Optional language for template generation.

    Returns:
        AgentResult with execution results.

    Example:
        result = vcoding.generate(
            "./my-project",
            "Create a fibonacci function",
            output="fibonacci.py"
        )
    """
    with workspace_context(target, language=language) as ws:
        result = ws.generate(prompt, output=output, agent=agent)
        return result


def run(
    target: str | Path,
    command: str,
    timeout: int | None = None,
    language: str | None = None,
) -> tuple[int, str, str]:
    """Run a command in a single call (one-shot API).

    This function handles the entire lifecycle: workspace creation,
    container start, file sync, command execution, and cleanup.

    Args:
        target: Path to the project directory.
        command: Command to execute.
        timeout: Optional timeout in seconds.
        language: Optional language for template generation.

    Returns:
        Tuple of (exit_code, stdout, stderr).

    Example:
        exit_code, stdout, stderr = vcoding.run(
            "./my-project",
            "python fibonacci.py"
        )
    """
    with workspace_context(target, language=language) as ws:
        return ws.run(command, timeout=timeout)
