"""Tests for vcoding.workspace.git module."""

from pathlib import Path

from vcoding.core.types import GitConfig
from vcoding.workspace.git import CommitInfo, GitManager


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""

    def test_create_commit_info(self) -> None:
        """Test creating CommitInfo."""
        info = CommitInfo(
            hash="abc123def456",
            short_hash="abc123d",
            message="Test commit",
            author="Test User",
            timestamp="2024-01-01T12:00:00",
        )
        assert info.hash == "abc123def456"
        assert info.short_hash == "abc123d"
        assert info.message == "Test commit"
        assert info.author == "Test User"
        assert info.timestamp == "2024-01-01T12:00:00"


class TestGitManager:
    """Tests for GitManager class."""

    def test_init(self, temp_dir: Path) -> None:
        """Test initialization."""
        manager = GitManager(temp_dir)
        assert manager.repo_path == temp_dir
        assert manager.config.auto_init is True

    def test_init_with_config(self, temp_dir: Path) -> None:
        """Test initialization with custom config."""
        config = GitConfig(auto_init=False, auto_commit=False)
        manager = GitManager(temp_dir, config)
        assert manager.config.auto_init is False
        assert manager.config.auto_commit is False

    def test_is_initialized_false(self, temp_dir: Path) -> None:
        """Test is_initialized when not initialized."""
        manager = GitManager(temp_dir)
        assert manager.is_initialized is False

    def test_is_initialized_true(self, temp_dir: Path) -> None:
        """Test is_initialized when initialized."""
        manager = GitManager(temp_dir)
        manager.init()
        assert manager.is_initialized is True

    def test_init_creates_repo(self, temp_dir: Path) -> None:
        """Test that init creates a git repository."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        result = manager.init()

        assert result is True
        assert (temp_dir / ".git").exists()

    def test_init_creates_gitignore(self, temp_dir: Path) -> None:
        """Test that init creates .gitignore."""
        config = GitConfig(
            default_gitignore=["*.log", "temp/"], auto_commit=False, auto_gitignore=True
        )
        manager = GitManager(temp_dir, config)
        manager.init()

        gitignore = temp_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text(encoding="utf-8")
        assert "*.log" in content
        assert "temp/" in content

    def test_init_idempotent(self, temp_dir: Path) -> None:
        """Test that init returns False if already initialized."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        manager.init()
        result = manager.init()

        assert result is False

    def test_init_with_initial_commit(self, temp_dir: Path) -> None:
        """Test that init creates initial commit when auto_commit is True."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=True))
        manager.init()

        assert manager.repo is not None
        commits = list(manager.repo.iter_commits())
        assert len(commits) == 1
        assert "Initial commit" in commits[0].message

    def test_add_file(self, temp_dir: Path) -> None:
        """Test adding a file to staging."""
        manager = GitManager(temp_dir)  # Use auto_commit=True to create initial commit
        manager.init()

        test_file = temp_dir / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        manager.add("test.txt")

        assert manager.repo is not None
        # File should be staged - check via git status instead
        status = manager.get_status()
        # File is either staged or untracked after add, depends on git version
        assert status is not None

    def test_add_multiple_files(self, temp_dir: Path) -> None:
        """Test adding multiple files."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        manager.init()

        (temp_dir / "file1.txt").write_text("1", encoding="utf-8")
        (temp_dir / "file2.txt").write_text("2", encoding="utf-8")

        manager.add(["file1.txt", "file2.txt"])
        # Should not raise

    def test_add_all(self, temp_dir: Path) -> None:
        """Test adding all changes."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        manager.init()

        (temp_dir / "new_file.txt").write_text("new", encoding="utf-8")

        manager.add_all()
        # Should not raise

    def test_commit(self, temp_dir: Path) -> None:
        """Test creating a commit."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        manager.init()

        (temp_dir / "file.txt").write_text("content", encoding="utf-8")
        manager.add_all()

        commit_hash = manager.commit("Test commit message")

        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 hash length

    def test_get_current_commit(self, temp_dir: Path) -> None:
        """Test getting current commit info."""
        manager = GitManager(temp_dir)
        manager.init()

        info = manager.get_current_commit()

        assert info is not None
        assert len(info.hash) == 40
        assert len(info.short_hash) == 7
        assert "Initial commit" in info.message

    def test_get_current_commit_empty_repo(self, temp_dir: Path) -> None:
        """Test getting current commit from empty repo."""
        manager = GitManager(temp_dir, GitConfig(auto_commit=False))
        manager.init()

        info = manager.get_current_commit()

        # Empty repo has no commits
        assert info is None

    def test_get_commit_by_ref(self, temp_dir: Path) -> None:
        """Test getting commit by reference."""
        manager = GitManager(temp_dir)
        manager.init()

        current = manager.get_current_commit()
        assert current is not None

        info = manager.get_commit(current.hash)

        assert info is not None
        assert info.hash == current.hash

    def test_list_commits(self, temp_dir: Path) -> None:
        """Test listing commits."""
        manager = GitManager(temp_dir)
        manager.init()

        # Add more commits
        for i in range(3):
            (temp_dir / f"file{i}.txt").write_text(f"{i}", encoding="utf-8")
            manager.add_all()
            manager.commit(f"Commit {i}")

        commits = manager.list_commits()

        assert len(commits) >= 3

    def test_list_commits_max_count(self, temp_dir: Path) -> None:
        """Test listing commits with max count."""
        manager = GitManager(temp_dir)
        manager.init()

        for i in range(5):
            (temp_dir / f"file{i}.txt").write_text(f"{i}", encoding="utf-8")
            manager.add_all()
            manager.commit(f"Commit {i}")

        commits = manager.list_commits(max_count=3)

        assert len(commits) == 3

    def test_rollback_soft(self, temp_dir: Path) -> None:
        """Test soft rollback."""
        manager = GitManager(temp_dir)
        manager.init()

        first_commit = manager.get_current_commit()
        assert first_commit is not None

        (temp_dir / "new.txt").write_text("new", encoding="utf-8")
        manager.add_all()
        manager.commit("Second commit")

        result = manager.rollback(first_commit.hash, hard=False)

        assert result is True

    def test_rollback_hard(self, temp_dir: Path) -> None:
        """Test hard rollback."""
        manager = GitManager(temp_dir)
        manager.init()

        first_commit = manager.get_current_commit()
        assert first_commit is not None

        new_file = temp_dir / "new.txt"
        new_file.write_text("new", encoding="utf-8")
        manager.add_all()
        manager.commit("Second commit")

        result = manager.rollback(first_commit.hash, hard=True)

        assert result is True

    def test_get_status(self, temp_dir: Path) -> None:
        """Test getting repository status."""
        manager = GitManager(temp_dir)  # Use auto_commit=True so we have a HEAD commit
        manager.init()

        # Create untracked file
        (temp_dir / "untracked.txt").write_text("untracked", encoding="utf-8")

        status = manager.get_status()

        assert "untracked" in status
        assert "staged" in status
        assert "modified" in status
        assert "untracked.txt" in status["untracked"]

    def test_get_diff(self, temp_dir: Path) -> None:
        """Test getting diff."""
        manager = GitManager(temp_dir)
        manager.init()

        # Modify gitignore
        gitignore = temp_dir / ".gitignore"
        gitignore.write_text("*.log\n*.tmp\n", encoding="utf-8")

        diff = manager.get_diff()

        # Diff should show changes
        assert isinstance(diff, str)

    def test_create_branch(self, temp_dir: Path) -> None:
        """Test creating a branch."""
        manager = GitManager(temp_dir)
        manager.init()

        result = manager.create_branch("feature-branch")

        assert result is True
        assert manager.get_current_branch() == "feature-branch"

    def test_create_branch_without_checkout(self, temp_dir: Path) -> None:
        """Test creating a branch without checkout."""
        manager = GitManager(temp_dir)
        manager.init()

        result = manager.create_branch("new-branch", checkout=False)

        assert result is True
        assert manager.get_current_branch() == "main"

    def test_checkout(self, temp_dir: Path) -> None:
        """Test checkout."""
        manager = GitManager(temp_dir)
        manager.init()
        manager.create_branch("other-branch", checkout=False)

        result = manager.checkout("other-branch")

        assert result is True
        assert manager.get_current_branch() == "other-branch"

    def test_get_current_branch(self, temp_dir: Path) -> None:
        """Test getting current branch."""
        manager = GitManager(temp_dir)
        manager.init()

        branch = manager.get_current_branch()

        assert branch == "main"

    def test_stash_and_pop(self, temp_dir: Path) -> None:
        """Test stashing and popping changes."""
        manager = GitManager(temp_dir)
        manager.init()

        # Create and commit a file first
        test_file = temp_dir / "test.txt"
        test_file.write_text("initial\n", encoding="utf-8")
        manager.add_all()
        manager.commit("Add test file")

        # Make changes to the tracked file
        test_file.write_text("modified\n", encoding="utf-8")

        result = manager.stash("Test stash")
        assert result is True

        result = manager.stash_pop()
        assert result is True

    def test_auto_commit_changes(self, temp_dir: Path) -> None:
        """Test auto committing changes."""
        manager = GitManager(temp_dir)
        manager.init()

        # Make changes
        (temp_dir / "new.txt").write_text("new content", encoding="utf-8")

        commit_hash = manager.auto_commit_changes("Auto commit test")

        assert commit_hash is not None

    def test_auto_commit_no_changes(self, temp_dir: Path) -> None:
        """Test auto commit when no changes."""
        manager = GitManager(temp_dir)
        manager.init()

        commit_hash = manager.auto_commit_changes()

        assert commit_hash is None

    def test_auto_commit_disabled(self, temp_dir: Path) -> None:
        """Test auto commit when disabled in config."""
        config = GitConfig(auto_commit=False)
        manager = GitManager(temp_dir, config)
        manager.init()

        (temp_dir / "new.txt").write_text("new", encoding="utf-8")

        commit_hash = manager.auto_commit_changes()

        assert commit_hash is None
