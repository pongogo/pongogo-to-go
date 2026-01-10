"""Integration tests for container path resolution.

Tests that all components (config, database, health check, discovery system)
correctly resolve paths in container deployments where:
- WORKDIR=/app (package location)
- Volume mount is /project/.pongogo (user's config)

These tests simulate the container environment by setting PONGOGO_KNOWLEDGE_PATH
and verifying all subsystems find their resources at the correct locations.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from mcp_server.config import get_project_root
from mcp_server.database import (
    PongogoDatabase,
    get_default_db_path,
    store_routing_event,
)
from mcp_server.health_check import check_config_validity, check_database_health


class TestContainerPathIntegration:
    """Integration tests for container deployment path resolution."""

    @pytest.fixture
    def container_env(self, tmp_path):
        """Set up simulated container environment.

        Creates:
        - /tmp/xxx/project/.pongogo/instructions/ (volume mount)
        - /tmp/xxx/project/.pongogo/config.yaml
        - Sets PONGOGO_KNOWLEDGE_PATH to simulate container
        """
        project_dir = tmp_path / "project"
        pongogo_dir = project_dir / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        # Create valid config
        config = {
            "routing": {"engine": "durian-0.6.1"},
            "knowledge": {"path": str(instructions_dir)},
        }
        config_path = pongogo_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Create a sample instruction file
        sample_category = instructions_dir / "test_category"
        sample_category.mkdir()
        (sample_category / "sample.instructions.md").write_text(
            "---\nid: test\n---\n# Test instruction"
        )

        return {
            "project_dir": project_dir,
            "pongogo_dir": pongogo_dir,
            "instructions_dir": instructions_dir,
            "config_path": config_path,
        }

    def test_project_root_resolution(self, container_env):
        """get_project_root() correctly derives from PONGOGO_KNOWLEDGE_PATH."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            root = get_project_root()

        assert root == container_env["project_dir"]

    def test_database_path_resolution(self, container_env):
        """Database path is correctly derived in container environment."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            db_path = get_default_db_path()

        expected = container_env["pongogo_dir"] / "pongogo.db"
        assert db_path == expected

    def test_database_creation_at_correct_location(self, container_env):
        """Database is created at correct location via env-derived path."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            db_path = get_default_db_path()
            db = PongogoDatabase(db_path=db_path)

        # Database should exist in the project's .pongogo directory
        assert db_path.exists()
        assert db_path.parent == container_env["pongogo_dir"]

        # Verify schema is created
        version = db.get_schema_version()
        assert version == "3.1.0"

    def test_routing_event_storage_at_correct_location(self, container_env):
        """Routing events are stored at correct location in container."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            db_path = get_default_db_path()

            # Store a routing event
            result = store_routing_event(
                user_message="How do I create an epic?",
                routed_instructions=["epic_management"],
                engine_version="durian-0.6.1",
                db_path=db_path,
            )

        assert result is True
        # Verify database was created in correct location
        assert (container_env["pongogo_dir"] / "pongogo.db").exists()

    def test_health_check_config_at_correct_location(self, container_env):
        """Health check finds config at correct location in container."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            result = check_config_validity()

        assert result["status"] == "valid"
        assert str(container_env["config_path"]) in result["path"]
        assert result["categories_count"] >= 1  # test_category created in fixture

    def test_health_check_database_at_correct_location(self, container_env):
        """Health check finds database at correct location in container."""
        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            # First create the database
            db_path = get_default_db_path()
            PongogoDatabase(db_path=db_path)

            # Then check health
            result = check_database_health()

        assert result["status"] == "healthy"
        assert str(container_env["pongogo_dir"]) in result["path"]
        assert result["writable"] is True

    def test_full_write_cycle(self, container_env):
        """Full write cycle works correctly in container environment.

        Tests:
        1. Database creation
        2. Routing event storage
        3. Event retrieval
        """
        from mcp_server.database import get_recent_events

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(container_env["instructions_dir"])},
            clear=True,
        ):
            db_path = get_default_db_path()

            # Store multiple events
            for i in range(3):
                store_routing_event(
                    user_message=f"Test message {i}",
                    routed_instructions=[f"instruction_{i}"],
                    engine_version="durian-0.6.1",
                    db_path=db_path,
                )

            # Retrieve events
            events = get_recent_events(limit=10, db_path=db_path)

        assert len(events) == 3
        # Verify all events have correct data
        messages = [e["user_message"] for e in events]
        assert "Test message 0" in messages
        assert "Test message 2" in messages


class TestPathMismatchDetection:
    """Tests to catch path mismatch issues early."""

    def test_no_hardcoded_cwd_in_database(self, tmp_path):
        """Database module doesn't rely on cwd for path resolution."""
        # Create project structure at different location than cwd
        project_dir = tmp_path / "project"
        pongogo_dir = project_dir / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        # Simulate being in /app while config is in /project
        app_dir = tmp_path / "app"
        app_dir.mkdir()

        with (
            patch.dict(
                os.environ,
                {"PONGOGO_KNOWLEDGE_PATH": str(instructions_dir)},
                clear=True,
            ),
            patch("mcp_server.config.Path.cwd", return_value=app_dir),
        ):
            # Even though we're "in" app_dir, database should go to project_dir
            db_path = get_default_db_path()

        # Database path should be in project_dir, NOT app_dir
        assert project_dir in db_path.parents or db_path.parent == pongogo_dir
        assert app_dir not in db_path.parents

    def test_no_hardcoded_home_in_container(self, tmp_path):
        """Database doesn't default to home when PONGOGO_KNOWLEDGE_PATH is set."""
        project_dir = tmp_path / "project"
        pongogo_dir = project_dir / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(instructions_dir)},
            clear=True,
        ):
            db_path = get_default_db_path()

        # Should NOT be in home directory
        assert Path.home() not in db_path.parents
        # Should be in project's .pongogo
        assert db_path == pongogo_dir / "pongogo.db"
