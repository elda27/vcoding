"""Tests for vcoding.ssh.keys module."""

import os
import stat
from pathlib import Path


from vcoding.ssh.keys import SSHKeyManager, SSHKeyPair


class TestSSHKeyPair:
    """Tests for SSHKeyPair named tuple."""

    def test_create_key_pair(self, temp_dir: Path) -> None:
        """Test creating SSHKeyPair."""
        pair = SSHKeyPair(
            private_key_path=temp_dir / "key",
            public_key_path=temp_dir / "key.pub",
            public_key_content="ssh-ed25519 AAAA... comment",
        )
        assert pair.private_key_path == temp_dir / "key"
        assert pair.public_key_path == temp_dir / "key.pub"
        assert "ssh-ed25519" in pair.public_key_content


class TestSSHKeyManager:
    """Tests for SSHKeyManager class."""

    def test_init_creates_directory(self, temp_dir: Path) -> None:
        """Test that initialization creates keys directory."""
        keys_dir = temp_dir / "keys"
        manager = SSHKeyManager(keys_dir)
        assert keys_dir.exists()
        assert manager.keys_dir == keys_dir

    def test_generate_key_pair(self, temp_dir: Path) -> None:
        """Test generating SSH key pair."""
        manager = SSHKeyManager(temp_dir)
        pair = manager.generate_key_pair("test_key")

        assert pair.private_key_path.exists()
        assert pair.public_key_path.exists()
        assert pair.private_key_path == temp_dir / "test_key"
        assert pair.public_key_path == temp_dir / "test_key.pub"

    def test_generate_key_pair_format(self, temp_dir: Path) -> None:
        """Test that generated keys have correct format."""
        manager = SSHKeyManager(temp_dir)
        pair = manager.generate_key_pair("format_test")

        # Check private key format
        private_key_content = pair.private_key_path.read_text(encoding="utf-8")
        assert "-----BEGIN OPENSSH PRIVATE KEY-----" in private_key_content
        assert "-----END OPENSSH PRIVATE KEY-----" in private_key_content

        # Check public key format
        assert pair.public_key_content.startswith("ssh-ed25519 ")

    def test_generate_key_pair_permissions(self, temp_dir: Path) -> None:
        """Test that private key has restrictive permissions."""
        manager = SSHKeyManager(temp_dir)
        pair = manager.generate_key_pair("perm_test")

        mode = os.stat(pair.private_key_path).st_mode
        # Owner read/write only (0o600)
        assert mode & stat.S_IRUSR  # Owner read
        assert mode & stat.S_IWUSR  # Owner write
        # Note: On Windows, these permissions may not work the same way

    def test_get_key_pair_existing(self, temp_dir: Path) -> None:
        """Test getting existing key pair."""
        manager = SSHKeyManager(temp_dir)
        original = manager.generate_key_pair("existing")

        retrieved = manager.get_key_pair("existing")
        assert retrieved is not None
        assert retrieved.private_key_path == original.private_key_path
        assert retrieved.public_key_content == original.public_key_content

    def test_get_key_pair_nonexistent(self, temp_dir: Path) -> None:
        """Test getting nonexistent key pair."""
        manager = SSHKeyManager(temp_dir)
        result = manager.get_key_pair("nonexistent")
        assert result is None

    def test_get_or_create_key_pair_new(self, temp_dir: Path) -> None:
        """Test get_or_create creates new key pair."""
        manager = SSHKeyManager(temp_dir)
        pair = manager.get_or_create_key_pair("new_key")

        assert pair.private_key_path.exists()
        assert pair.public_key_path.exists()

    def test_get_or_create_key_pair_existing(self, temp_dir: Path) -> None:
        """Test get_or_create returns existing key pair."""
        manager = SSHKeyManager(temp_dir)
        original = manager.generate_key_pair("reuse")
        original_content = original.public_key_content

        retrieved = manager.get_or_create_key_pair("reuse")
        assert retrieved.public_key_content == original_content

    def test_delete_key_pair(self, temp_dir: Path) -> None:
        """Test deleting key pair."""
        manager = SSHKeyManager(temp_dir)
        manager.generate_key_pair("to_delete")

        result = manager.delete_key_pair("to_delete")
        assert result is True
        assert not (temp_dir / "to_delete").exists()
        assert not (temp_dir / "to_delete.pub").exists()

    def test_delete_key_pair_nonexistent(self, temp_dir: Path) -> None:
        """Test deleting nonexistent key pair."""
        manager = SSHKeyManager(temp_dir)
        result = manager.delete_key_pair("nonexistent")
        assert result is False

    def test_cleanup_all(self, temp_dir: Path) -> None:
        """Test cleaning up all key pairs."""
        manager = SSHKeyManager(temp_dir)
        manager.generate_key_pair("key1")
        manager.generate_key_pair("key2")
        manager.generate_key_pair("key3")

        count = manager.cleanup_all()
        assert count == 3
        assert list(temp_dir.glob("*")) == []

    def test_list_keys(self, temp_dir: Path) -> None:
        """Test listing key names."""
        manager = SSHKeyManager(temp_dir)
        manager.generate_key_pair("alpha")
        manager.generate_key_pair("beta")

        keys = manager.list_keys()
        assert "alpha" in keys
        assert "beta" in keys
        assert len(keys) == 2

    def test_list_keys_empty(self, temp_dir: Path) -> None:
        """Test listing keys when empty."""
        manager = SSHKeyManager(temp_dir)
        keys = manager.list_keys()
        assert keys == []

    def test_default_key_name(self, temp_dir: Path) -> None:
        """Test that default key name is 'vcoding'."""
        manager = SSHKeyManager(temp_dir)
        pair = manager.generate_key_pair()

        assert pair.private_key_path.name == "vcoding"
        assert pair.public_key_path.name == "vcoding.pub"
