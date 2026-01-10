"""Unit tests for CLI init command.

Tests database initialization behavior that occurs during pongogo init.
Note: init_command.py requires typer which may not be available in test env,
so we test the database initialization behavior directly.
"""

import sqlite3


class TestDatabaseInitialization:
    """Tests for database initialization during init."""

    def test_database_created_during_init(self, tmp_path):
        """Database should be created with schema during init."""
        from mcp_server.database import PongogoDatabase

        # Create database as init command does
        db = PongogoDatabase(project_root=tmp_path)

        # Verify database file exists
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        assert db_path.exists()

        # Verify schema is correct
        version = db.get_schema_version()
        assert version == "3.1.0"

    def test_database_tables_exist(self, tmp_path):
        """All expected tables should exist after init."""
        from mcp_server.database import PongogoDatabase

        PongogoDatabase(project_root=tmp_path)
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_tables = [
            "routing_events",
            "routing_triggers",
            "artifact_discovered",
            "observation_discovered",
            "schema_info",
        ]
        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"

    def test_database_is_empty_after_init(self, tmp_path):
        """Database tables should be empty after init."""
        from mcp_server.database import PongogoDatabase

        PongogoDatabase(project_root=tmp_path)
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM routing_events")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    def test_health_check_passes_after_init(self, tmp_path, monkeypatch):
        """Health check should show healthy after init creates database."""
        from mcp_server.database import PongogoDatabase
        from mcp_server.health_check import check_database_health

        # Clear env vars
        monkeypatch.delenv("PONGOGO_KNOWLEDGE_PATH", raising=False)
        monkeypatch.delenv("PONGOGO_PROJECT_ROOT", raising=False)

        # Create .pongogo directory and config (health check needs this)
        pongogo_dir = tmp_path / ".pongogo"
        pongogo_dir.mkdir(parents=True)
        config_path = pongogo_dir / "config.yaml"
        config_path.write_text("routing:\n  engine: durian-0.6.1\n")

        # Initialize database as init command does
        PongogoDatabase(project_root=tmp_path)
        db_path = pongogo_dir / "pongogo.db"

        # Mock the db path function
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: db_path,
        )

        result = check_database_health()

        assert result["status"] == "healthy"
        assert result["writable"] is True
