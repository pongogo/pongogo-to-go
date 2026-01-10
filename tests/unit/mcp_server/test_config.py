"""Unit tests for MCP server config module.

Tests YAML configuration loading, environment variable overrides,
and path resolution.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from mcp_server.config import (
    DEFAULT_CONFIG,
    ConfigurationError,
    _deep_merge,
    _resolve_path,
    get_core_instructions_path,
    get_knowledge_path,
    get_project_root,
    get_routing_config,
    load_config,
)


class TestDeepMerge:
    """Tests for _deep_merge helper function."""

    def test_merge_simple_dicts(self):
        """Merge simple flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = _deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Merge nested dictionaries."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3}}

        result = _deep_merge(base, override)

        assert result == {"outer": {"a": 1, "b": 3}}

    def test_merge_does_not_modify_base(self):
        """Merge should not modify the base dictionary."""
        base = {"a": 1}
        override = {"b": 2}
        original_base = base.copy()

        _deep_merge(base, override)

        assert base == original_base


class TestResolvePath:
    """Tests for _resolve_path helper function."""

    def test_resolve_none_returns_none(self, tmp_path: Path):
        """Resolve None returns None."""
        result = _resolve_path(None, tmp_path)
        assert result is None

    def test_resolve_absolute_path(self, tmp_path: Path):
        """Resolve absolute path returns it unchanged."""
        absolute = "/absolute/path/to/file"
        result = _resolve_path(absolute, tmp_path)
        assert result == Path(absolute)

    def test_resolve_relative_path(self, tmp_path: Path):
        """Resolve relative path makes it absolute from base_dir."""
        result = _resolve_path("relative/path", tmp_path)
        expected = (tmp_path / "relative/path").resolve()
        assert result == expected


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG structure."""

    def test_default_has_routing(self):
        """Default config should have routing section."""
        assert "routing" in DEFAULT_CONFIG
        assert "engine" in DEFAULT_CONFIG["routing"]
        assert "limit_default" in DEFAULT_CONFIG["routing"]

    def test_default_has_knowledge(self):
        """Default config should have knowledge section."""
        assert "knowledge" in DEFAULT_CONFIG
        assert "path" in DEFAULT_CONFIG["knowledge"]

    def test_default_has_server(self):
        """Default config should have server section."""
        assert "server" in DEFAULT_CONFIG
        assert "log_level" in DEFAULT_CONFIG["server"]

    def test_default_engine_is_none(self):
        """Default engine should be None (use registered default)."""
        assert DEFAULT_CONFIG["routing"]["engine"] is None

    def test_default_limit_is_5(self):
        """Default routing limit should be 5."""
        assert DEFAULT_CONFIG["routing"]["limit_default"] == 5


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_returns_defaults_without_file(self, tmp_path: Path):
        """Load returns defaults when no config file exists."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config(server_dir=tmp_path)

        assert config["routing"]["limit_default"] == 5

    def test_load_from_explicit_path(self, tmp_path: Path):
        """Load reads from explicit config path."""
        config_path = tmp_path / "custom-config.yaml"
        config_content = {"routing": {"limit_default": 10}}
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)

        config = load_config(str(config_path), server_dir=tmp_path)

        assert config["routing"]["limit_default"] == 10

    def test_load_from_env_var(self, tmp_path: Path):
        """Load reads from PONGOGO_CONFIG_PATH env var."""
        config_path = tmp_path / "env-config.yaml"
        config_content = {"server": {"log_level": "DEBUG"}}
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)

        with patch.dict(os.environ, {"PONGOGO_CONFIG_PATH": str(config_path)}):
            config = load_config(server_dir=tmp_path)

        assert config["server"]["log_level"] == "DEBUG"

    def test_load_knowledge_path_override(self, tmp_path: Path):
        """Load respects PONGOGO_KNOWLEDGE_PATH env var."""
        custom_path = str(tmp_path / "custom-knowledge")

        with patch.dict(
            os.environ, {"PONGOGO_KNOWLEDGE_PATH": custom_path}, clear=True
        ):
            config = load_config(server_dir=tmp_path)

        assert custom_path in config["knowledge"]["path"]

    def test_load_default_config_file(self, tmp_path: Path):
        """Load reads pongogo-config.yaml from server_dir."""
        config_path = tmp_path / "pongogo-config.yaml"
        config_content = {"routing": {"engine": "durian-0.5"}}
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)

        with patch.dict(os.environ, {}, clear=True):
            config = load_config(server_dir=tmp_path)

        assert config["routing"]["engine"] == "durian-0.5"

    def test_load_invalid_yaml_raises(self, tmp_path: Path):
        """Load raises ConfigurationError for invalid YAML."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            load_config(str(config_path), server_dir=tmp_path)

    def test_load_merges_with_defaults(self, tmp_path: Path):
        """Load merges file config with defaults."""
        config_path = tmp_path / "partial.yaml"
        # Only specify routing engine, other values should come from defaults
        config_content = {"routing": {"engine": "durian-0.5"}}
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)

        config = load_config(str(config_path), server_dir=tmp_path)

        # Custom value
        assert config["routing"]["engine"] == "durian-0.5"
        # Default value preserved
        assert config["routing"]["limit_default"] == 5


class TestGetKnowledgePath:
    """Tests for get_knowledge_path function."""

    def test_returns_configured_path(self, tmp_path: Path):
        """Returns path from config if specified."""
        custom_path = str(tmp_path / "knowledge")
        config = {"knowledge": {"path": custom_path}}

        result = get_knowledge_path(config, server_dir=tmp_path)

        assert result == Path(custom_path)

    def test_returns_default_path(self, tmp_path: Path):
        """Returns default path if not configured."""
        config = {"knowledge": {"path": None}}

        result = get_knowledge_path(config, server_dir=tmp_path)

        # Default is ../knowledge/instructions relative to server_dir
        expected = (tmp_path.parent / "knowledge" / "instructions").resolve()
        assert result == expected


class TestGetRoutingConfig:
    """Tests for get_routing_config function."""

    def test_extracts_routing_section(self):
        """Extracts routing config for create_router."""
        config = {
            "routing": {
                "engine": "durian-0.5",
                "features": {"violation_detection": True},
                "limit_default": 10,  # Should not be included
            }
        }

        result = get_routing_config(config)

        assert result["routing"]["engine"] == "durian-0.5"
        assert result["routing"]["features"]["violation_detection"] is True
        assert "limit_default" not in result["routing"]

    def test_handles_missing_sections(self):
        """Handles missing routing section gracefully."""
        config = {}

        result = get_routing_config(config)

        assert result["routing"]["engine"] is None
        assert result["routing"]["features"] == {}


class TestGetCoreInstructionsPath:
    """Tests for get_core_instructions_path function."""

    def test_returns_path_or_none(self):
        """Returns Path or None depending on existence."""
        result = get_core_instructions_path()
        # Either returns a Path that exists or None
        if result is not None:
            assert isinstance(result, Path)


class TestGetProjectRoot:
    """Tests for get_project_root function.

    Critical for container deployments where:
    - WORKDIR is /app (package location)
    - Volume mount is /project/.pongogo (user's config)
    """

    def test_derives_from_knowledge_path(self, tmp_path: Path):
        """Derives project root from PONGOGO_KNOWLEDGE_PATH."""
        # Simulate: /project/.pongogo/instructions -> /project
        knowledge_path = tmp_path / ".pongogo" / "instructions"
        knowledge_path.mkdir(parents=True)

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(knowledge_path)},
            clear=True,
        ):
            result = get_project_root()

        assert result == tmp_path

    def test_explicit_project_root_override(self, tmp_path: Path):
        """PONGOGO_PROJECT_ROOT takes precedence."""
        explicit_root = tmp_path / "explicit"
        explicit_root.mkdir()
        knowledge_path = tmp_path / "other" / ".pongogo" / "instructions"
        knowledge_path.mkdir(parents=True)

        with patch.dict(
            os.environ,
            {
                "PONGOGO_PROJECT_ROOT": str(explicit_root),
                "PONGOGO_KNOWLEDGE_PATH": str(knowledge_path),
            },
            clear=True,
        ):
            result = get_project_root()

        # Explicit override takes precedence
        assert result == explicit_root

    def test_fallback_to_cwd(self, tmp_path: Path):
        """Falls back to cwd when no env vars set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("mcp_server.config.Path.cwd", return_value=tmp_path),
        ):
            result = get_project_root()

        assert result == tmp_path

    def test_container_path_simulation(self, tmp_path: Path):
        """Simulates container deployment path resolution.

        Container scenario:
        - WORKDIR=/app (where Python runs)
        - Volume: /project/.pongogo mounted
        - PONGOGO_KNOWLEDGE_PATH=/project/.pongogo/instructions
        - Expected: project root = /project
        """
        # Create simulated container structure
        project_dir = tmp_path / "project"
        pongogo_dir = project_dir / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        # Create config file
        config_file = pongogo_dir / "config.yaml"
        config_file.write_text("routing:\n  engine: durian-0.6.1\n")

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(instructions_dir)},
            clear=True,
        ):
            result = get_project_root()

        assert result == project_dir
        # Verify we can find config from this root
        assert (result / ".pongogo" / "config.yaml").exists()
