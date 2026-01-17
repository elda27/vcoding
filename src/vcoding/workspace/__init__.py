"""Workspace management layer for vcoding."""

from vcoding.workspace.git import GitManager
from vcoding.workspace.workspace import Workspace

__all__ = [
    "GitManager",
    "Workspace",
]
