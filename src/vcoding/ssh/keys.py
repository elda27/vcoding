"""SSH key generation and management."""

import os
import stat
from pathlib import Path
from typing import NamedTuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class SSHKeyPair(NamedTuple):
    """SSH key pair."""

    private_key_path: Path
    public_key_path: Path
    public_key_content: str


class SSHKeyManager:
    """Manages SSH key generation, storage, and cleanup."""

    def __init__(self, keys_dir: Path) -> None:
        """Initialize SSH key manager.

        Args:
            keys_dir: Directory to store SSH keys.
        """
        self._keys_dir = keys_dir
        self._keys_dir.mkdir(parents=True, exist_ok=True)

    @property
    def keys_dir(self) -> Path:
        """Get keys directory."""
        return self._keys_dir

    def generate_key_pair(self, name: str = "vcoding") -> SSHKeyPair:
        """Generate a new Ed25519 SSH key pair.

        Args:
            name: Base name for the key files.

        Returns:
            SSHKeyPair with paths and public key content.
        """
        # Generate Ed25519 key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )

        # Write private key
        private_key_path = self._keys_dir / name
        private_key_path.write_bytes(private_key_bytes)
        # Set restrictive permissions (owner read/write only)
        os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)

        # Write public key
        public_key_path = self._keys_dir / f"{name}.pub"
        public_key_content = public_key_bytes.decode("utf-8")
        public_key_path.write_text(public_key_content, encoding="utf-8")

        return SSHKeyPair(
            private_key_path=private_key_path,
            public_key_path=public_key_path,
            public_key_content=public_key_content,
        )

    def get_key_pair(self, name: str = "vcoding") -> SSHKeyPair | None:
        """Get existing key pair.

        Args:
            name: Base name for the key files.

        Returns:
            SSHKeyPair if exists, None otherwise.
        """
        private_key_path = self._keys_dir / name
        public_key_path = self._keys_dir / f"{name}.pub"

        if not private_key_path.exists() or not public_key_path.exists():
            return None

        public_key_content = public_key_path.read_text(encoding="utf-8")

        return SSHKeyPair(
            private_key_path=private_key_path,
            public_key_path=public_key_path,
            public_key_content=public_key_content,
        )

    def get_or_create_key_pair(self, name: str = "vcoding") -> SSHKeyPair:
        """Get existing or create new key pair.

        Args:
            name: Base name for the key files.

        Returns:
            SSHKeyPair.
        """
        existing = self.get_key_pair(name)
        if existing:
            return existing
        return self.generate_key_pair(name)

    def delete_key_pair(self, name: str = "vcoding") -> bool:
        """Delete a key pair.

        Args:
            name: Base name for the key files.

        Returns:
            True if deleted, False if not found.
        """
        private_key_path = self._keys_dir / name
        public_key_path = self._keys_dir / f"{name}.pub"

        deleted = False
        if private_key_path.exists():
            private_key_path.unlink()
            deleted = True
        if public_key_path.exists():
            public_key_path.unlink()
            deleted = True

        return deleted

    def cleanup_all(self) -> int:
        """Delete all key pairs in the keys directory.

        Returns:
            Number of key pairs deleted.
        """
        count = 0
        for key_file in self._keys_dir.glob("*"):
            if key_file.is_file():
                key_file.unlink()
                count += 1
        return count // 2  # Each pair has 2 files

    def list_keys(self) -> list[str]:
        """List all key names in the keys directory.

        Returns:
            List of key names (without .pub extension).
        """
        keys = set()
        for key_file in self._keys_dir.glob("*"):
            if key_file.is_file():
                name = key_file.stem if key_file.suffix == ".pub" else key_file.name
                keys.add(name)
        return sorted(keys)
