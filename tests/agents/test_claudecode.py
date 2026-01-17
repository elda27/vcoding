"""Tests for vcoding.agents.claudecode module."""

from unittest.mock import MagicMock

import pytest

from vcoding.agents.claudecode import ClaudeCodeAgent
from vcoding.ssh.client import SSHClient


class TestClaudeCodeAgent:
    """Tests for ClaudeCodeAgent class."""

    @pytest.fixture
    def mock_ssh_client(self) -> MagicMock:
        """Create mock SSH client."""
        client = MagicMock(spec=SSHClient)
        client.execute.return_value = (0, "", "")
        return client

    @pytest.fixture
    def agent(self, mock_ssh_client: MagicMock) -> ClaudeCodeAgent:
        """Create Claude Code agent for testing."""
        return ClaudeCodeAgent(mock_ssh_client)

    def test_name(self, agent: ClaudeCodeAgent) -> None:
        """Test agent name."""
        assert agent.name == "claude-code"

    def test_is_installed_true(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed when claude is installed."""
        mock_ssh_client.execute.return_value = (0, "/usr/local/bin/claude", "")

        assert agent.is_installed is True

    def test_is_installed_false(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed when claude is not installed."""
        mock_ssh_client.execute.return_value = (1, "", "not found")

        assert agent.is_installed is False

    def test_execute_basic(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test basic execute."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (0, "Claude response", ""),  # claude command
        ]

        result = agent.execute("Hello, Claude")

        assert result.success is True
        assert result.stdout == "Claude response"

    def test_execute_with_options(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with options."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (0, '{"response": "test"}', ""),  # claude command
        ]

        result = agent.execute(
            "Write code",
            options={"output_format": "json", "max_turns": 5},
        )

        assert result.success is True
        assert result.metadata["output_format"] == "json"

    def test_execute_failure(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute when command fails."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (1, "", "API error"),  # claude failed
        ]

        result = agent.execute("test prompt")

        assert result.success is False
        assert result.exit_code == 1

    def test_run_claude(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test run_claude helper method."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "Response text", ""),
        ]

        result = agent.run_claude("Explain this code")

        assert result.success is True
        assert "Response text" in result.stdout

    def test_run_with_context(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test run_with_context method."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (0, "Analysis complete", ""),  # claude command
            (0, "", ""),  # find modified files
        ]

        result = agent.run_with_context(
            "Analyze this code",
            context_files=["main.py", "utils.py"],
            workdir="/workspace",
        )

        assert result.success is True

    def test_execute_with_model_option(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with model option."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]

        result = agent.execute(
            "test",
            options={"model": "claude-sonnet-4-20250514"},
        )

        assert result.success is True
        assert result.metadata["model"] == "claude-sonnet-4-20250514"

    def test_execute_with_permission_mode(
        self, agent: ClaudeCodeAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with permission mode."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]

        result = agent.execute(
            "Edit the file",
            options={"permission_mode": "acceptEdits"},
        )

        assert result.success is True
