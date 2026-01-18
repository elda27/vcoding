"""Tests for vcoding.functions module."""

from pathlib import Path

from vcoding.core.types import VirtualizationType, WorkspaceConfig


class TestCreateWorkspace:
    """Tests for create_workspace function."""

    def test_create_workspace(self, temp_dir: Path) -> None:
        """Test creating a workspace."""
        from vcoding.functions import create_workspace

        workspace = create_workspace(
            target=temp_dir,
            name="test-workspace",
        )

        assert workspace is not None
        assert workspace.name == "test-workspace"
        assert workspace.target_path == temp_dir

    def test_create_workspace_with_config(
        self, temp_dir: Path, sample_workspace_config: WorkspaceConfig
    ) -> None:
        """Test creating workspace with custom config."""
        from vcoding.functions import create_workspace

        workspace = create_workspace(
            target=temp_dir,
            config=sample_workspace_config,
        )

        assert workspace.config == sample_workspace_config
        assert workspace.name == sample_workspace_config.name

    def test_create_workspace_with_language(self, temp_dir: Path) -> None:
        """Test creating workspace with language for templates."""
        from vcoding.functions import create_workspace

        workspace = create_workspace(
            target=temp_dir,
            name="py-workspace",
            language="python",
        )

        assert workspace is not None
        # Dockerfile and gitignore should be generated
        assert (temp_dir / "Dockerfile").exists()
        assert (temp_dir / ".gitignore").exists()


class TestStartStopWorkspace:
    """Tests for start/stop workspace functions."""

    def test_stop_workspace_has_function(self) -> None:
        """Test stop_workspace function exists."""
        from vcoding.functions import stop_workspace

        assert callable(stop_workspace)

    def test_destroy_workspace_has_function(self) -> None:
        """Test destroy_workspace function exists."""
        from vcoding.functions import destroy_workspace

        assert callable(destroy_workspace)


class TestExecuteCommand:
    """Tests for execute_command function."""

    def test_execute_command_has_function(self) -> None:
        """Test execute_command function exists."""
        from vcoding.functions import execute_command

        assert callable(execute_command)


class TestRunAgent:
    """Tests for run_agent function."""

    def test_run_agent_has_function(self) -> None:
        """Test run_agent function exists."""
        from vcoding.functions import run_agent

        assert callable(run_agent)


class TestSyncFunctions:
    """Tests for sync functions."""

    def test_sync_to_workspace_has_function(self) -> None:
        """Test sync_to_workspace function exists."""
        from vcoding.functions import sync_to_workspace

        assert callable(sync_to_workspace)

    def test_sync_from_workspace_has_function(self) -> None:
        """Test sync_from_workspace function exists."""
        from vcoding.functions import sync_from_workspace

        assert callable(sync_from_workspace)


class TestCommitChanges:
    """Tests for commit_changes function."""

    def test_commit_changes_has_function(self) -> None:
        """Test commit_changes function exists."""
        from vcoding.functions import commit_changes

        assert callable(commit_changes)


class TestRollback:
    """Tests for rollback function."""

    def test_rollback_has_function(self) -> None:
        """Test rollback function exists."""
        from vcoding.functions import rollback

        assert callable(rollback)


class TestGetCommits:
    """Tests for get_commits function."""

    def test_get_commits_has_function(self) -> None:
        """Test get_commits function exists."""
        from vcoding.functions import get_commits

        assert callable(get_commits)


class TestGenerateTemplates:
    """Tests for generate_templates function."""

    def test_generate_templates(self, temp_dir: Path) -> None:
        """Test generating templates."""
        from vcoding.functions import generate_templates

        generated = generate_templates(
            project_path=temp_dir,
            language="python",
        )

        assert "dockerfile" in generated or "gitignore" in generated
        assert (temp_dir / "Dockerfile").exists()
        assert (temp_dir / ".gitignore").exists()

    def test_generate_templates_dockerfile_only(self, temp_dir: Path) -> None:
        """Test generating only Dockerfile."""
        from vcoding.functions import generate_templates

        generated = generate_templates(
            project_path=temp_dir,
            language="python",
            gitignore=False,
        )

        assert (temp_dir / "Dockerfile").exists()
        # gitignore may or may not exist depending on prior state

    def test_generate_templates_gitignore_only(self, temp_dir: Path) -> None:
        """Test generating only gitignore."""
        from vcoding.functions import generate_templates

        generated = generate_templates(
            project_path=temp_dir,
            language="python",
            dockerfile=False,
        )

        assert (temp_dir / ".gitignore").exists()


class TestExtendDockerfile:
    """Tests for extend_dockerfile function."""

    def test_extend_dockerfile(self, temp_dir: Path) -> None:
        """Test extending a Dockerfile."""
        from vcoding.functions import extend_dockerfile

        # Create original Dockerfile
        original = temp_dir / "Dockerfile.orig"
        original.write_text(
            "FROM python:3.11\nRUN pip install pytest\n", encoding="utf-8"
        )

        output = temp_dir / "Dockerfile.extended"
        result = extend_dockerfile(
            dockerfile_path=original,
            output_path=output,
            user="testuser",
        )

        assert result == output
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "FROM python:3.11" in content


class TestWorkspaceContext:
    """Tests for workspace_context context manager."""

    def test_workspace_context_has_class(self) -> None:
        """Test workspace_context class exists."""
        from vcoding.functions import workspace_context

        assert workspace_context is not None

    def test_workspace_context_init(self, temp_dir: Path) -> None:
        """Test workspace_context initialization."""
        from vcoding.functions import workspace_context

        ctx = workspace_context(temp_dir, name="test-ctx")
        assert ctx._target == temp_dir
        assert ctx._name == "test-ctx"
        assert ctx._auto_destroy is False
