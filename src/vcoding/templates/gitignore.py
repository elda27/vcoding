"""Gitignore template generation."""

from typing import ClassVar


class GitignoreTemplate:
    """Gitignore template generator."""

    # Common patterns for all projects
    COMMON_PATTERNS: ClassVar[list[str]] = [
        "# OS files",
        ".DS_Store",
        "Thumbs.db",
        "*.swp",
        "*.swo",
        "*~",
        "",
        "# IDE",
        ".idea/",
        ".vscode/",
        "*.sublime-project",
        "*.sublime-workspace",
        "",
        "# vcoding",
        ".vcoding/keys/",
        ".vcoding/temp/",
        ".vcoding/logs/",
        "",
        "# Environment",
        ".env",
        ".env.local",
        ".env.*.local",
        "*.env",
    ]

    # Language-specific patterns
    LANGUAGE_PATTERNS: ClassVar[dict[str, list[str]]] = {
        "python": [
            "",
            "# Python",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "build/",
            "develop-eggs/",
            "dist/",
            "downloads/",
            "eggs/",
            ".eggs/",
            "lib/",
            "lib64/",
            "parts/",
            "sdist/",
            "var/",
            "wheels/",
            "*.egg-info/",
            ".installed.cfg",
            "*.egg",
            "",
            "# Virtual environments",
            ".venv/",
            "venv/",
            "ENV/",
            "env/",
            "",
            "# pytest",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            "",
            "# mypy",
            ".mypy_cache/",
            "",
            "# Jupyter",
            ".ipynb_checkpoints/",
        ],
        "nodejs": [
            "",
            "# Node.js",
            "node_modules/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            ".npm",
            ".yarn-integrity",
            "",
            "# Build",
            "dist/",
            "build/",
            ".next/",
            "out/",
            "",
            "# Testing",
            "coverage/",
            ".nyc_output/",
        ],
        "go": [
            "",
            "# Go",
            "*.exe",
            "*.exe~",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.test",
            "*.out",
            "go.work",
            "vendor/",
        ],
        "rust": [
            "",
            "# Rust",
            "/target/",
            "Cargo.lock",
            "**/*.rs.bk",
        ],
        "java": [
            "",
            "# Java",
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "*.log",
            "",
            "# Maven",
            "target/",
            "pom.xml.tag",
            "pom.xml.releaseBackup",
            "pom.xml.versionsBackup",
            "",
            "# Gradle",
            ".gradle/",
            "build/",
            "!gradle-wrapper.jar",
        ],
    }

    def __init__(self) -> None:
        """Initialize gitignore template."""
        self._patterns: list[str] = list(self.COMMON_PATTERNS)
        self._languages: list[str] = []
        self._custom_patterns: list[str] = []

    def with_language(self, language: str) -> "GitignoreTemplate":
        """Add language-specific patterns.

        Args:
            language: Language name.

        Returns:
            Self for chaining.
        """
        lang_lower = language.lower()
        if lang_lower in self.LANGUAGE_PATTERNS and lang_lower not in self._languages:
            self._languages.append(lang_lower)
        return self

    def with_pattern(self, pattern: str) -> "GitignoreTemplate":
        """Add a custom pattern.

        Args:
            pattern: Gitignore pattern.

        Returns:
            Self for chaining.
        """
        self._custom_patterns.append(pattern)
        return self

    def with_patterns(self, patterns: list[str]) -> "GitignoreTemplate":
        """Add multiple custom patterns.

        Args:
            patterns: List of gitignore patterns.

        Returns:
            Self for chaining.
        """
        self._custom_patterns.extend(patterns)
        return self

    def render(self) -> str:
        """Render the gitignore file.

        Returns:
            Complete .gitignore content.
        """
        lines = list(self._patterns)

        # Add language patterns
        for lang in self._languages:
            lines.extend(self.LANGUAGE_PATTERNS[lang])

        # Add custom patterns
        if self._custom_patterns:
            lines.append("")
            lines.append("# Custom patterns")
            lines.extend(self._custom_patterns)

        return "\n".join(lines) + "\n"

    @classmethod
    def for_language(cls, language: str) -> "GitignoreTemplate":
        """Create a template for a specific language.

        Args:
            language: Programming language.

        Returns:
            Configured GitignoreTemplate.
        """
        template = cls()
        template.with_language(language)
        return template

    @classmethod
    def for_languages(cls, languages: list[str]) -> "GitignoreTemplate":
        """Create a template for multiple languages.

        Args:
            languages: List of programming languages.

        Returns:
            Configured GitignoreTemplate.
        """
        template = cls()
        for lang in languages:
            template.with_language(lang)
        return template

    @classmethod
    def default(cls) -> "GitignoreTemplate":
        """Create a default template with common patterns only.

        Returns:
            GitignoreTemplate with common patterns.
        """
        return cls()
