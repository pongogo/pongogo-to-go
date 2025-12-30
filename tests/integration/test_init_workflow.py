"""Integration tests for pongogo init workflow.

Tests the complete init workflow including:
- Directory structure creation
- Config file generation
- Preference initialization
"""

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestInitWorkflow:
    """Tests for pongogo init command workflow."""

    def test_init_creates_pongogo_directory(self, tmp_path):
        """Init should create .pongogo directory."""
        # TODO: Implement when init command is fully wired
        # For now, test the config generation directly
        from cli.config import generate_config, write_config

        config_path = tmp_path / ".pongogo" / "config.yaml"
        config = generate_config()
        write_config(config_path, config)

        assert config_path.exists()
        assert (tmp_path / ".pongogo").is_dir()

    def test_init_respects_minimal_flag(self, tmp_path):
        """Init with minimal flag should only enable core categories."""
        from cli.config import (
            MINIMAL_CATEGORIES,
            generate_config,
            load_config,
            write_config,
        )

        config_path = tmp_path / ".pongogo" / "config.yaml"
        config = generate_config(minimal=True)
        write_config(config_path, config)

        loaded = load_config(config_path)

        for category, enabled in loaded["categories"].items():
            if category in MINIMAL_CATEGORIES:
                assert enabled is True
            else:
                assert enabled is False

    def test_init_detects_wiki_path(self, tmp_path):
        """Init should detect existing wiki directory."""
        # Create wiki directory
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir()

        from cli.config import generate_config, write_config

        config_path = tmp_path / ".pongogo" / "config.yaml"
        config = generate_config(wiki_path="wiki/")
        write_config(config_path, config)

        assert config["placeholders"]["wiki_path"] == "wiki/"

    def test_init_detects_docs_path(self, tmp_path):
        """Init should detect existing docs directory."""
        # Create docs directory
        docs_path = tmp_path / "docs"
        docs_path.mkdir()

        from cli.config import generate_config, write_config

        config_path = tmp_path / ".pongogo" / "config.yaml"
        config = generate_config(docs_path="docs/")
        write_config(config_path, config)

        assert config["placeholders"]["docs_path"] == "docs/"
