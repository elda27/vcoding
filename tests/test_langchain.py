"""Tests for vcoding.langchain module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Check if langchain is available before running tests
try:
    import langchain

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Skip all tests in this module if langchain is not installed
pytestmark = pytest.mark.skipif(
    not LANGCHAIN_AVAILABLE, reason="LangChain is not installed"
)


class TestLangChainToolsAvailability:
    """Tests for LangChain tools availability."""

    def test_langchain_module_imports(self) -> None:
        """Test that langchain module can be imported."""
        import vcoding.langchain

        assert hasattr(vcoding.langchain, "get_langchain_tools")

    def test_get_langchain_tools(self, temp_dir: Path) -> None:
        """Test getting LangChain tools."""
        from vcoding.langchain import get_langchain_tools
        from vcoding.workspace.workspace import Workspace

        workspace = Workspace(temp_dir, name="langchain-test")
        workspace.initialize()

        tools = get_langchain_tools(workspace)

        assert isinstance(tools, list)
        assert len(tools) > 0


class TestLangChainToolsFunctionality:
    """Tests for LangChain tools functionality."""

    @pytest.fixture
    def mock_workspace(self, temp_dir: Path) -> MagicMock:
        """Create mock workspace for tool testing."""
        workspace = MagicMock()
        workspace.project_path = temp_dir
        workspace.name = "test-workspace"
        workspace.is_running = True
        workspace.manager = MagicMock()
        workspace.manager.vcoding_dir = temp_dir / ".vcoding"
        workspace.git = MagicMock()
        workspace.ssh = MagicMock()
        return workspace

    def test_execute_command_tool(self, mock_workspace: MagicMock) -> None:
        """Test ExecuteCommandTool."""
        from vcoding.langchain import get_langchain_tools

        mock_workspace.execute.return_value = (0, "hello", "")

        tools = get_langchain_tools(mock_workspace)

        # Find execute tool
        execute_tool = next((t for t in tools if "execute" in t.name.lower()), None)
        assert execute_tool is not None

    def test_git_commit_tool(self, mock_workspace: MagicMock) -> None:
        """Test GitCommitTool."""
        from vcoding.langchain import get_langchain_tools

        mock_workspace.commit_changes.return_value = "abc123"

        tools = get_langchain_tools(mock_workspace)

        # Find git commit tool
        git_tool = next(
            (t for t in tools if "commit" in t.name.lower()),
            None,
        )
        assert git_tool is not None


class TestLangChainWithMockedWorkspace:
    """Tests using mocked workspace for complete tool testing."""

    @pytest.fixture
    def started_mock_workspace(self, temp_dir: Path) -> MagicMock:
        """Create a mock workspace that appears started."""
        workspace = MagicMock()
        workspace.project_path = temp_dir
        workspace.name = "started-workspace"
        workspace.is_running = True
        workspace.container_id = "container-123"
        workspace.manager = MagicMock()
        workspace.manager.vcoding_dir = temp_dir / ".vcoding"
        (temp_dir / ".vcoding").mkdir(parents=True, exist_ok=True)
        workspace.git = MagicMock()
        workspace.git.auto_commit_changes.return_value = "commit-hash"
        workspace.git.list_commits.return_value = []
        workspace.git.get_status.return_value = {
            "staged": [],
            "modified": [],
            "untracked": [],
        }
        workspace.ssh = MagicMock()
        workspace.execute.return_value = (0, "output", "")
        workspace.run_agent.return_value = MagicMock(success=True, stdout="output")
        workspace.commit_changes.return_value = "commit-hash"
        workspace.rollback_to.return_value = True
        return workspace

    def test_all_tools_have_names(self, started_mock_workspace: MagicMock) -> None:
        """Test that all tools have valid names."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)

        for tool in tools:
            assert hasattr(tool, "name")
            assert tool.name is not None
            assert len(tool.name) > 0

    def test_all_tools_have_descriptions(
        self, started_mock_workspace: MagicMock
    ) -> None:
        """Test that all tools have descriptions."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)

        for tool in tools:
            assert hasattr(tool, "description")
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_are_invokable(self, started_mock_workspace: MagicMock) -> None:
        """Test that tools have invoke/run methods."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)

        for tool in tools:
            # LangChain tools should have these methods
            assert (
                hasattr(tool, "run") or hasattr(tool, "_run") or hasattr(tool, "invoke")
            )

    def test_execute_tool_run(self, started_mock_workspace: MagicMock) -> None:
        """Test execute tool can be run."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)
        execute_tool = next((t for t in tools if "execute" in t.name.lower()), None)

        assert execute_tool is not None
        result = execute_tool._run("echo hello")

        assert "Exit code: 0" in result
        started_mock_workspace.execute.assert_called()

    def test_git_commit_tool_run(self, started_mock_workspace: MagicMock) -> None:
        """Test git commit tool can be run."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)
        commit_tool = next((t for t in tools if "commit" in t.name.lower()), None)

        assert commit_tool is not None
        result = commit_tool._run("test commit")

        assert "Successfully committed" in result
        started_mock_workspace.commit_changes.assert_called_with("test commit")

    def test_git_rollback_tool_run(self, started_mock_workspace: MagicMock) -> None:
        """Test git rollback tool can be run."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)
        rollback_tool = next((t for t in tools if "rollback" in t.name.lower()), None)

        assert rollback_tool is not None
        result = rollback_tool._run("abc123")

        assert "Successfully rolled back" in result
        started_mock_workspace.rollback_to.assert_called_with("abc123", hard=False)

    def test_copilot_tool_run(self, started_mock_workspace: MagicMock) -> None:
        """Test copilot tool can be run."""
        from vcoding.langchain import get_langchain_tools

        tools = get_langchain_tools(started_mock_workspace)
        copilot_tool = next((t for t in tools if "copilot" in t.name.lower()), None)

        assert copilot_tool is not None
        result = copilot_tool._run("how to list files")

        assert "output" in result
        started_mock_workspace.run_agent.assert_called()
