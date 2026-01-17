"""Code agents layer for vcoding."""

from vcoding.agents.base import AgentResult, CodeAgent
from vcoding.agents.claudecode import ClaudeCodeAgent
from vcoding.agents.copilot import CopilotAgent

__all__ = [
    "AgentResult",
    "ClaudeCodeAgent",
    "CodeAgent",
    "CopilotAgent",
]
