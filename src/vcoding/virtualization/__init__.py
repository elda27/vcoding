"""Virtualization layer for vcoding."""

from vcoding.virtualization.base import VirtualizationBackend
from vcoding.virtualization.docker import DockerBackend, DockerNotAvailableError

__all__ = [
    "DockerBackend",
    "DockerNotAvailableError",
    "VirtualizationBackend",
]
