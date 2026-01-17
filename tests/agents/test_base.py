"""Tests for vcoding.agents.base module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.ssh.client import SSHClient


class ConcreteAgent(CodeAgent):
    """Concrete implementation for testing."""

    @property
    def name(self) -> str:
        return "test-agent"

    @property
    def is_installed(self) -> bool:
        return self._check_command_exists("test-cmd")

    def install(self) -> bool:
        exit_code, _, _ = self._execute_command("install test-agent")
        return exit_code == 0

    def execute(
        self,
        prompt: str,
        workdir: str | None = None,
        context_files: list[str] | None = None,
        options: dict | None = None,
    ) -> AgentResult:
        exit_code, stdout, stderr = self._execute_command(
            f"run {prompt}", workdir=workdir
        )
        return AgentResult(
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_create_success_result(self) -> None:
        """Test creating successful result."""
        result = AgentResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.files_modified == []
        assert result.files_created == []
        assert result.files_deleted == []
        assert result.metadata == {}

    def test_create_failure_result(self) -> None:
        """Test creating failure result."""
        result = AgentResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="error message",
        )
        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "error message"

    def test_with_files(self) -> None:
        """Test result with file changes."""
        result = AgentResult(
            success=True,
            exit_code=0,
            stdout="",
            stderr="",
            files_modified=["file1.py", "file2.py"],
            files_created=["new.py"],
            files_deleted=["old.py"],
        )
        assert result.files_modified == ["file1.py", "file2.py"]
        assert result.files_created == ["new.py"]
        assert result.files_deleted == ["old.py"]

    def test_with_metadata(self) -> None:
        """Test result with metadata."""
        result = AgentResult(
            success=True,
            exit_code=0,
            stdout="",
            stderr="",
            metadata={"prompt": "test", "duration": 1.5},
        )
        assert result.metadata["prompt"] == "test"
        assert result.metadata["duration"] == 1.5


class TestCodeAgent:
    """Tests for CodeAgent abstract class."""

    @pytest.fixture
    def mock_ssh_client(self, temp_dir: Path) -> MagicMock:
        """Create mock SSH client."""
        client = MagicMock(spec=SSHClient)
        client.execute.return_value = (0, "ok", "")
        return client

    @pytest.fixture
    def agent(self, mock_ssh_client: MagicMock) -> ConcreteAgent:
        """Create concrete agent for testing."""
        return ConcreteAgent(mock_ssh_client)

    def test_init(self, agent: ConcreteAgent, mock_ssh_client: MagicMock) -> None:
        """Test initialization."""
        assert agent.ssh_client == mock_ssh_client

    def test_name_property(self, agent: ConcreteAgent) -> None:
        """Test name property."""
        assert agent.name == "test-agent"

    def test_execute_command(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test command execution through SSH."""
        mock_ssh_client.execute.return_value = (0, "output", "")

        exit_code, stdout, stderr = agent._execute_command("test command")

        assert exit_code == 0
        assert stdout == "output"
        mock_ssh_client.execute.assert_called_once()

    def test_execute_command_with_options(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test command execution with all options."""
        agent._execute_command(
            "cmd",
            workdir="/app",
            env={"VAR": "value"},
            timeout=60,
        )

        mock_ssh_client.execute.assert_called_with(
            "cmd",
            workdir="/app",
            env={"VAR": "value"},
            timeout=60,
        )

    def test_check_command_exists_true(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test checking command exists when it does."""
        mock_ssh_client.execute.return_value = (0, "/usr/bin/cmd", "")

        assert agent._check_command_exists("cmd") is True

    def test_check_command_exists_false(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test checking command exists when it doesn't."""
        mock_ssh_client.execute.return_value = (1, "", "not found")

        assert agent._check_command_exists("nonexistent") is False

    def test_is_installed(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed property."""
        mock_ssh_client.execute.return_value = (0, "/path/to/test-cmd", "")
        assert agent.is_installed is True

        mock_ssh_client.execute.return_value = (1, "", "")
        assert agent.is_installed is False

    def test_install(self, agent: ConcreteAgent, mock_ssh_client: MagicMock) -> None:
        """Test install method."""
        mock_ssh_client.execute.return_value = (0, "", "")
        assert agent.install() is True

        mock_ssh_client.execute.return_value = (1, "", "error")
        assert agent.install() is False

    def test_execute(self, agent: ConcreteAgent, mock_ssh_client: MagicMock) -> None:
        """Test execute method."""
        mock_ssh_client.execute.return_value = (0, "result", "")

        result = agent.execute("test prompt")

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "result"

    def test_execute_with_workdir(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with working directory."""
        mock_ssh_client.execute.return_value = (0, "", "")

        agent.execute("prompt", workdir="/custom/dir")

        call_args = mock_ssh_client.execute.call_args
        assert call_args[1]["workdir"] == "/custom/dir"

    def test_get_modified_files(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test getting modified files."""
        mock_ssh_client.execute.return_value = (0, "/app/file1.py\n/app/file2.py\n", "")

        files = agent.get_modified_files("/app", "/tmp/marker")

        assert len(files) == 2
        assert "/app/file1.py" in files
        assert "/app/file2.py" in files

    def test_get_modified_files_empty(
        self, agent: ConcreteAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test getting modified files when none exist."""
        mock_ssh_client.execute.return_value = (0, "", "")

        files = agent.get_modified_files("/app", "/tmp/marker")

        assert files == []
