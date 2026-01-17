"""Virtualization layer for vcoding."""

from vcoding.virtualization.base import VirtualizationBackend
from vcoding.virtualization.docker import DockerBackend

__all__ = [
    "DockerBackend",
    "VirtualizationBackend",
]
