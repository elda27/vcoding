"""Tests for vcoding.templates.gitignore module."""


from vcoding.templates.gitignore import GitignoreTemplate


class TestGitignoreTemplate:
    """Tests for GitignoreTemplate class."""

    def test_init(self) -> None:
        """Test default initialization."""
        template = GitignoreTemplate()
        assert len(template._patterns) > 0
        assert template._languages == []
        assert template._custom_patterns == []

    def test_common_patterns(self) -> None:
        """Test that common patterns are included."""
        template = GitignoreTemplate()
        content = template.render()

        assert ".DS_Store" in content
        assert "Thumbs.db" in content
        assert ".env" in content
        assert ".vcoding/keys/" in content

    def test_with_language_chaining(self) -> None:
        """Test method chaining for with_language."""
        template = GitignoreTemplate()
        result = template.with_language("python")
        assert result is template
        assert "python" in template._languages

    def test_with_pattern_chaining(self) -> None:
        """Test method chaining for with_pattern."""
        template = GitignoreTemplate()
        result = template.with_pattern("*.custom")
        assert result is template
        assert "*.custom" in template._custom_patterns

    def test_with_patterns_chaining(self) -> None:
        """Test method chaining for with_patterns."""
        template = GitignoreTemplate()
        result = template.with_patterns(["*.a", "*.b"])
        assert result is template
        assert "*.a" in template._custom_patterns
        assert "*.b" in template._custom_patterns

    def test_render_python(self) -> None:
        """Test rendering with Python patterns."""
        template = GitignoreTemplate().with_language("python")
        content = template.render()

        assert "__pycache__/" in content
        assert "*.py[cod]" in content  # Matches *.pyc, *.pyo, *.pyd
        assert ".venv/" in content
        assert ".pytest_cache/" in content

    def test_render_nodejs(self) -> None:
        """Test rendering with Node.js patterns."""
        template = GitignoreTemplate().with_language("nodejs")
        content = template.render()

        assert "node_modules/" in content
        assert "npm-debug.log" in content

    def test_render_go(self) -> None:
        """Test rendering with Go patterns."""
        template = GitignoreTemplate().with_language("go")
        content = template.render()

        assert "*.exe" in content
        assert "vendor/" in content

    def test_render_rust(self) -> None:
        """Test rendering with Rust patterns."""
        template = GitignoreTemplate().with_language("rust")
        content = template.render()

        assert "/target/" in content
        assert "Cargo.lock" in content

    def test_render_java(self) -> None:
        """Test rendering with Java patterns."""
        template = GitignoreTemplate().with_language("java")
        content = template.render()

        assert "*.class" in content
        assert "*.jar" in content
        assert "target/" in content

    def test_render_custom_patterns(self) -> None:
        """Test rendering with custom patterns."""
        template = GitignoreTemplate()
        template.with_pattern("*.log")
        template.with_pattern("build/")
        content = template.render()

        assert "*.log" in content
        assert "build/" in content
        assert "# Custom patterns" in content

    def test_render_ends_with_newline(self) -> None:
        """Test that rendered content ends with newline."""
        template = GitignoreTemplate()
        content = template.render()

        assert content.endswith("\n")

    def test_for_language(self) -> None:
        """Test creating template for specific language."""
        template = GitignoreTemplate.for_language("python")
        content = template.render()

        assert "__pycache__/" in content

    def test_for_languages(self) -> None:
        """Test creating template for multiple languages."""
        template = GitignoreTemplate.for_languages(["python", "nodejs"])
        content = template.render()

        assert "__pycache__/" in content
        assert "node_modules/" in content

    def test_default(self) -> None:
        """Test creating default template."""
        template = GitignoreTemplate.default()
        content = template.render()

        assert ".DS_Store" in content
        assert "__pycache__/" not in content  # No language-specific

    def test_unknown_language_ignored(self) -> None:
        """Test that unknown languages are ignored."""
        template = GitignoreTemplate()
        template.with_language("unknown_lang")
        assert "unknown_lang" not in template._languages

    def test_duplicate_language_ignored(self) -> None:
        """Test that duplicate languages are ignored."""
        template = GitignoreTemplate()
        template.with_language("python")
        template.with_language("python")
        assert template._languages.count("python") == 1

    def test_ide_patterns(self) -> None:
        """Test IDE-specific patterns are included."""
        template = GitignoreTemplate()
        content = template.render()

        assert ".idea/" in content
        assert ".vscode/" in content

    def test_vcoding_patterns(self) -> None:
        """Test vcoding-specific patterns are included."""
        template = GitignoreTemplate()
        content = template.render()

        assert ".vcoding/keys/" in content
        assert ".vcoding/temp/" in content
        assert ".vcoding/logs/" in content
