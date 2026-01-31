"""Git repository management."""

from dataclasses import dataclass
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from vcoding.core.types import GitConfig


@dataclass
class CommitInfo:
    """Git commit information."""

    hash: str
    short_hash: str
    message: str
    author: str
    timestamp: str


class GitManager:
    """Manages Git repository operations."""

    def __init__(self, repo_path: Path, config: GitConfig | None = None) -> None:
        """Initialize Git manager.

        Args:
            repo_path: Path to the repository.
            config: Git configuration.
        """
        self._repo_path = Path(repo_path).resolve()
        self._config = config or GitConfig()
        self._repo: Repo | None = None

    @property
    def repo_path(self) -> Path:
        """Get repository path."""
        return self._repo_path

    @property
    def config(self) -> GitConfig:
        """Get Git configuration."""
        return self._config

    @property
    def repo(self) -> Repo | None:
        """Get Git repository object."""
        if self._repo is None:
            try:
                self._repo = Repo(self._repo_path)
            except InvalidGitRepositoryError:
                pass
        return self._repo

    @property
    def is_initialized(self) -> bool:
        """Check if repository is initialized."""
        return (self._repo_path / ".git").exists()

    def init(self, initial_branch: str = "main") -> bool:
        """Initialize Git repository.

        Args:
            initial_branch: Name of the initial branch.

        Returns:
            True if initialized, False if already exists.
        """
        if self.is_initialized:
            return False

        self._repo = Repo.init(self._repo_path, initial_branch=initial_branch)

        # Create default .gitignore only if configured
        if self._config.auto_gitignore:
            self._create_default_gitignore()

        # Initial commit
        if self._config.auto_commit:
            self.add_all()
            self.commit("Initial commit")

        return True

    def _create_default_gitignore(self) -> None:
        """Create default .gitignore file."""
        gitignore_path = self._repo_path / ".gitignore"
        if not gitignore_path.exists():
            content = "\n".join(self._config.default_gitignore) + "\n"
            gitignore_path.write_text(content, encoding="utf-8")

    def add(self, paths: str | list[str]) -> None:
        """Add files to staging area.

        Args:
            paths: File path(s) to add.
        """
        if self.repo is None:
            raise ValueError("Repository not initialized")

        if isinstance(paths, str):
            paths = [paths]

        self.repo.index.add(paths)

    def add_all(self) -> None:
        """Add all changes to staging area."""
        if self.repo is None:
            raise ValueError("Repository not initialized")

        self.repo.git.add("-A")

    def commit(self, message: str, author: str | None = None) -> str:
        """Create a commit.

        Args:
            message: Commit message.
            author: Author string (e.g., "Name <email>").

        Returns:
            Commit hash.
        """
        if self.repo is None:
            raise ValueError("Repository not initialized")

        commit = self.repo.index.commit(message, author=author)
        return commit.hexsha

    def get_current_commit(self) -> CommitInfo | None:
        """Get current HEAD commit info.

        Returns:
            CommitInfo or None if no commits.
        """
        if self.repo is None or self.repo.head.is_detached:
            return None

        try:
            commit = self.repo.head.commit
            message = commit.message
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            return CommitInfo(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:7],
                message=message.strip(),
                author=str(commit.author),
                timestamp=commit.committed_datetime.isoformat(),
            )
        except Exception:
            return None

    def get_commit(self, ref: str) -> CommitInfo | None:
        """Get commit info by reference.

        Args:
            ref: Commit hash or reference.

        Returns:
            CommitInfo or None if not found.
        """
        if self.repo is None:
            return None

        try:
            commit = self.repo.commit(ref)
            message = commit.message
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            return CommitInfo(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:7],
                message=message.strip(),
                author=str(commit.author),
                timestamp=commit.committed_datetime.isoformat(),
            )
        except Exception:
            return None

    def list_commits(self, max_count: int = 50) -> list[CommitInfo]:
        """List recent commits.

        Args:
            max_count: Maximum number of commits to return.

        Returns:
            List of CommitInfo.
        """
        if self.repo is None:
            return []

        try:
            commits = list(self.repo.iter_commits(max_count=max_count))
            result = []
            for c in commits:
                message = c.message
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                result.append(
                    CommitInfo(
                        hash=c.hexsha,
                        short_hash=c.hexsha[:7],
                        message=message.strip(),
                        author=str(c.author),
                        timestamp=c.committed_datetime.isoformat(),
                    )
                )
            return result
        except Exception:
            return []

    def rollback(self, ref: str, hard: bool = False) -> bool:
        """Rollback to a specific commit.

        Args:
            ref: Commit hash or reference.
            hard: If True, discard all changes. If False, keep changes as staged.

        Returns:
            True if successful.
        """
        if self.repo is None:
            return False

        try:
            mode = "--hard" if hard else "--soft"
            self.repo.git.reset(mode, ref)
            return True
        except GitCommandError:
            return False

    def get_status(self) -> dict[str, list[str]]:
        """Get repository status.

        Returns:
            Dictionary with 'staged', 'modified', 'untracked' file lists.
        """
        if self.repo is None:
            return {"staged": [], "modified": [], "untracked": []}

        return {
            "staged": [
                item.a_path for item in self.repo.index.diff("HEAD") if item.a_path
            ],
            "modified": [
                item.a_path for item in self.repo.index.diff(None) if item.a_path
            ],
            "untracked": list(self.repo.untracked_files),
        }

    def get_diff(self, ref: str | None = None) -> str:
        """Get diff from a reference.

        Args:
            ref: Commit reference. If None, shows working tree diff.

        Returns:
            Diff string.
        """
        if self.repo is None:
            return ""

        try:
            if ref:
                return self.repo.git.diff(ref)
            return self.repo.git.diff()
        except GitCommandError:
            return ""

    def create_branch(self, name: str, checkout: bool = True) -> bool:
        """Create a new branch.

        Args:
            name: Branch name.
            checkout: Whether to checkout the new branch.

        Returns:
            True if successful.
        """
        if self.repo is None:
            return False

        try:
            branch = self.repo.create_head(name)
            if checkout:
                branch.checkout()
            return True
        except Exception:
            return False

    def checkout(self, ref: str) -> bool:
        """Checkout a branch or commit.

        Args:
            ref: Branch name or commit hash.

        Returns:
            True if successful.
        """
        if self.repo is None:
            return False

        try:
            self.repo.git.checkout(ref)
            return True
        except GitCommandError:
            return False

    def get_current_branch(self) -> str | None:
        """Get current branch name.

        Returns:
            Branch name or None if detached HEAD.
        """
        if self.repo is None:
            return None

        try:
            return self.repo.active_branch.name
        except TypeError:
            return None  # Detached HEAD

    def stash(self, message: str | None = None) -> bool:
        """Stash current changes.

        Args:
            message: Optional stash message.

        Returns:
            True if successful.
        """
        if self.repo is None:
            return False

        try:
            if message:
                self.repo.git.stash("push", "-m", message)
            else:
                self.repo.git.stash()
            return True
        except GitCommandError:
            return False

    def stash_pop(self) -> bool:
        """Pop the latest stash.

        Returns:
            True if successful.
        """
        if self.repo is None:
            return False

        try:
            self.repo.git.stash("pop")
            return True
        except GitCommandError:
            return False

    def auto_commit_changes(
        self, message: str = "Auto-commit by vcoding"
    ) -> str | None:
        """Add all changes and commit if there are changes.

        Args:
            message: Commit message.

        Returns:
            Commit hash if committed, None if no changes.
        """
        if self.repo is None or not self._config.auto_commit:
            return None

        status = self.get_status()
        if not any(status.values()):
            return None

        self.add_all()
        return self.commit(message)
