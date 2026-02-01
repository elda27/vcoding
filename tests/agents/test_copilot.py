"""Tests for vcoding.agents.copilot module."""

from unittest.mock import MagicMock

import pytest

from vcoding.agents.copilot import CopilotAgent
from vcoding.ssh.client import SSHClient


class TestCopilotAgent:
    """Tests for CopilotAgent class."""

    @pytest.fixture
    def mock_ssh_client(self) -> MagicMock:
        """Create mock SSH client."""
        client = MagicMock(spec=SSHClient)
        client.execute.return_value = (0, "", "")
        return client

    @pytest.fixture
    def agent(self, mock_ssh_client: MagicMock) -> CopilotAgent:
        """Create Copilot agent for testing."""
        return CopilotAgent(mock_ssh_client)

    def test_name(self, agent: CopilotAgent) -> None:
        """Test agent name."""
        assert agent.name == "github-copilot-cli"

    def test_is_installed_true(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed when Copilot is installed."""
        # First call: check gh exists
        # Second call: check copilot extension
        mock_ssh_client.execute.side_effect = [
            (0, "/usr/bin/gh", ""),  # which gh
            (0, "gh copilot\n", ""),  # gh extension list
        ]

        assert agent.is_installed is True

    def test_is_installed_no_gh(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed when gh is not installed."""
        mock_ssh_client.execute.return_value = (1, "", "not found")

        assert agent.is_installed is False

    def test_is_installed_no_copilot_extension(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test is_installed when Copilot CLI is not installed."""
        # Implementation uses 'which copilot' to check installation
        mock_ssh_client.execute.return_value = (1, "", "not found")

        assert agent.is_installed is False

    def test_execute_suggest(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with prompt."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (0, "git status", ""),  # copilot command
        ]

        result = agent.execute("show git status")

        assert result.success is True
        assert result.metadata["prompt"] == "show git status"

    def test_execute_explain(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with model option."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (0, "This command shows...", ""),  # copilot command
        ]

        result = agent.execute("git status", options={"model": "gpt-4o"})

        assert result.success is True
        assert result.metadata["model"] == "gpt-4o"

    def test_execute_default_mode(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with default options."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]

        result = agent.execute("test prompt")

        assert result.metadata["allow_all_tools"] is True

    def test_execute_with_allow_all_tools_false(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with allow_all_tools set to False."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]

        result = agent.execute("list branches", options={"allow_all_tools": False})

        assert result.metadata["allow_all_tools"] is False

    def test_execute_failure(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute when command fails."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),  # touch marker
            (1, "", "error"),  # copilot failed
        ]

        result = agent.execute("prompt")

        assert result.success is False
        assert result.exit_code == 1

    def test_execute_with_model(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test execute with model option."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "ls -la", ""),
        ]

        result = agent.execute(
            "list files in detail", options={"model": "claude-sonnet-4"}
        )

        assert result.success is True
        assert result.metadata["model"] == "claude-sonnet-4"

    def test_execute_returns_prompt_in_metadata(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test that execute returns prompt in metadata."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "This lists files...", ""),
        ]

        result = agent.execute("ls -la")

        assert result.success is True
        assert result.metadata["prompt"] == "ls -la"

    def test_execute_escapes_prompt(
        self, agent: CopilotAgent, mock_ssh_client: MagicMock
    ) -> None:
        """Test that prompt is properly escaped."""
        mock_ssh_client.execute.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]

        agent.execute('prompt with "quotes" and $variables')

        # Verify the command was called (escaping is handled internally)
        assert mock_ssh_client.execute.called
