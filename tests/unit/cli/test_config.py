"""Unit tests for CLI config module.

Tests YAML parsing, config generation, validation, and defaults.
"""

from pathlib import Path

import pytest
import yaml

from cli.config import (
    DEFAULT_CONFIG,
    MINIMAL_CATEGORIES,
    generate_config,
    load_config,
    write_config,
)


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG structure."""

    def test_default_config_has_version(self):
        """Default config should have version."""
        assert "version" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["version"] == "1.0.0"

    def test_default_config_has_categories(self):
        """Default config should have categories."""
        assert "categories" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["categories"], dict)

    def test_default_config_has_placeholders(self):
        """Default config should have placeholders."""
        assert "placeholders" in DEFAULT_CONFIG
        assert "wiki_path" in DEFAULT_CONFIG["placeholders"]
        assert "docs_path" in DEFAULT_CONFIG["placeholders"]

    def test_all_categories_enabled_by_default(self):
        """All categories should be enabled by default."""
        for category, enabled in DEFAULT_CONFIG["categories"].items():
            assert enabled is True, f"Category {category} should be enabled by default"


class TestMinimalCategories:
    """Tests for MINIMAL_CATEGORIES constant."""

    def test_minimal_categories_is_set(self):
        """Minimal categories should be a set."""
        assert isinstance(MINIMAL_CATEGORIES, set)

    def test_minimal_categories_subset_of_default(self):
        """Minimal categories should be subset of default categories."""
        default_categories = set(DEFAULT_CONFIG["categories"].keys())
        assert MINIMAL_CATEGORIES.issubset(default_categories)

    def test_minimal_includes_software_engineering(self):
        """Minimal should include software_engineering."""
        assert "software_engineering" in MINIMAL_CATEGORIES

    def test_minimal_includes_safety_prevention(self):
        """Minimal should include safety_prevention."""
        assert "safety_prevention" in MINIMAL_CATEGORIES


class TestGenerateConfig:
    """Tests for generate_config function."""

    def test_generate_default_config(self):
        """Generate config with defaults."""
        config = generate_config()
        assert config["version"] == "1.0.0"
        assert all(config["categories"].values())

    def test_generate_minimal_config(self):
        """Generate minimal config with only core categories."""
        config = generate_config(minimal=True)

        for category, enabled in config["categories"].items():
            if category in MINIMAL_CATEGORIES:
                assert enabled is True
            else:
                assert enabled is False

    def test_generate_with_wiki_path(self):
        """Generate config with custom wiki path."""
        config = generate_config(wiki_path="custom/wiki/")
        assert config["placeholders"]["wiki_path"] == "custom/wiki/"

    def test_generate_with_docs_path(self):
        """Generate config with custom docs path."""
        config = generate_config(docs_path="custom/docs/")
        assert config["placeholders"]["docs_path"] == "custom/docs/"

    def test_generate_does_not_modify_defaults(self):
        """Generate config should not modify DEFAULT_CONFIG."""
        original_categories = DEFAULT_CONFIG["categories"].copy()
        generate_config(minimal=True)
        assert DEFAULT_CONFIG["categories"] == original_categories


class TestWriteConfig:
    """Tests for write_config function."""

    def test_write_creates_file(self, tmp_path: Path):
        """Write config should create file."""
        config_path = tmp_path / ".pongogo" / "config.yaml"
        config = generate_config()

        write_config(config_path, config)

        assert config_path.exists()

    def test_write_creates_parent_directories(self, tmp_path: Path):
        """Write config should create parent directories."""
        config_path = tmp_path / "deep" / "nested" / "config.yaml"
        config = generate_config()

        write_config(config_path, config)

        assert config_path.parent.exists()

    def test_write_includes_header(self, tmp_path: Path):
        """Written config should include header comment."""
        config_path = tmp_path / "config.yaml"
        config = generate_config()

        write_config(config_path, config)

        content = config_path.read_text()
        assert content.startswith("# Pongogo Configuration")

    def test_write_produces_valid_yaml(self, tmp_path: Path):
        """Written config should be valid YAML."""
        config_path = tmp_path / "config.yaml"
        config = generate_config()

        write_config(config_path, config)

        # Should parse without error
        loaded = yaml.safe_load(config_path.read_text())
        assert loaded["version"] == config["version"]


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path):
        """Load valid config file."""
        config_path = tmp_path / "config.yaml"
        original = generate_config()
        write_config(config_path, original)

        loaded = load_config(config_path)

        assert loaded["version"] == original["version"]
        assert loaded["categories"] == original["categories"]

    def test_load_minimal_config(self, tmp_path: Path):
        """Load minimal config file."""
        config_path = tmp_path / "config.yaml"
        original = generate_config(minimal=True)
        write_config(config_path, original)

        loaded = load_config(config_path)

        # Check minimal categories
        for category, enabled in loaded["categories"].items():
            if category in MINIMAL_CATEGORIES:
                assert enabled is True
            else:
                assert enabled is False

    def test_load_config_with_custom_paths(self, tmp_path: Path):
        """Load config with custom placeholder paths."""
        config_path = tmp_path / "config.yaml"
        original = generate_config(wiki_path="my-wiki/", docs_path="my-docs/")
        write_config(config_path, original)

        loaded = load_config(config_path)

        assert loaded["placeholders"]["wiki_path"] == "my-wiki/"
        assert loaded["placeholders"]["docs_path"] == "my-docs/"

    def test_load_nonexistent_raises(self, tmp_path: Path):
        """Load nonexistent config should raise FileNotFoundError."""
        config_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path)
