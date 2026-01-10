"""Tests for health_check module."""

import sqlite3

from mcp_server.health_check import (
    check_config_validity,
    check_container_status,
    check_database_health,
    check_event_capture,
    get_health_status,
)


class TestCheckContainerStatus:
    """Tests for check_container_status function."""

    def test_returns_dict(self):
        """Should return dictionary with status."""
        result = check_container_status()
        assert isinstance(result, dict)
        assert "status" in result

    def test_status_is_valid_value(self):
        """Status should be healthy, unhealthy, or unknown."""
        result = check_container_status()
        assert result["status"] in ("healthy", "unhealthy", "unknown")

    def test_includes_containerized_flag(self):
        """Should include containerized flag."""
        result = check_container_status()
        assert "containerized" in result


class TestCheckDatabaseHealth:
    """Tests for check_database_health function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return dictionary with status."""
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "events.db",
        )

        result = check_database_health()
        assert isinstance(result, dict)
        assert "status" in result

    def test_missing_when_no_database(self, tmp_path, monkeypatch):
        """Should report missing when database doesn't exist."""
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "nonexistent.db",
        )

        result = check_database_health()
        assert result["status"] == "missing"
        assert result["writable"] is False

    def test_healthy_when_database_accessible(self, tmp_path, monkeypatch):
        """Should report healthy when database is accessible."""
        db_path = tmp_path / "events.db"
        # Create a valid database
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE routing_events (id INTEGER PRIMARY KEY)")
        conn.close()

        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: db_path,
        )

        result = check_database_health()
        assert result["status"] == "healthy"
        assert result["writable"] is True


class TestCheckEventCapture:
    """Tests for check_event_capture function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return dictionary with status."""
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "events.db",
        )

        result = check_event_capture()
        assert isinstance(result, dict)
        assert "status" in result

    def test_unknown_when_no_database(self, tmp_path, monkeypatch):
        """Should report unknown when database doesn't exist."""
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "nonexistent.db",
        )

        result = check_event_capture()
        assert result["status"] == "unknown"
        assert result["total_count"] == 0

    def test_empty_when_no_events(self, tmp_path, monkeypatch):
        """Should report empty when database has no events."""
        db_path = tmp_path / "events.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE routing_events (id INTEGER PRIMARY KEY, timestamp TEXT)"
        )
        conn.close()

        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: db_path,
        )

        result = check_event_capture()
        assert result["status"] == "empty"
        assert result["total_count"] == 0


class TestCheckConfigValidity:
    """Tests for check_config_validity function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return dictionary with status."""
        monkeypatch.chdir(tmp_path)

        result = check_config_validity()
        assert isinstance(result, dict)
        assert "status" in result

    def test_missing_when_no_pongogo_dir(self, tmp_path, monkeypatch):
        """Should report missing when .pongogo doesn't exist."""
        # Clear env vars so get_project_root falls back to cwd
        monkeypatch.delenv("PONGOGO_KNOWLEDGE_PATH", raising=False)
        monkeypatch.delenv("PONGOGO_PROJECT_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = check_config_validity()
        assert result["status"] == "missing"

    def test_missing_when_no_config_file(self, tmp_path, monkeypatch):
        """Should report missing when config.yaml doesn't exist."""
        # Clear env vars so get_project_root falls back to cwd
        monkeypatch.delenv("PONGOGO_KNOWLEDGE_PATH", raising=False)
        monkeypatch.delenv("PONGOGO_PROJECT_ROOT", raising=False)
        pongogo_dir = tmp_path / ".pongogo"
        pongogo_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        result = check_config_validity()
        assert result["status"] == "missing"

    def test_valid_when_config_exists(self, tmp_path, monkeypatch):
        """Should report valid when config.yaml is valid YAML."""
        # Clear env vars so get_project_root falls back to cwd
        monkeypatch.delenv("PONGOGO_KNOWLEDGE_PATH", raising=False)
        monkeypatch.delenv("PONGOGO_PROJECT_ROOT", raising=False)
        pongogo_dir = tmp_path / ".pongogo"
        pongogo_dir.mkdir()
        config_path = pongogo_dir / "config.yaml"
        config_path.write_text("routing:\n  engine: durian-0.6.1\n")
        monkeypatch.chdir(tmp_path)

        result = check_config_validity()
        assert result["status"] == "valid"

    def test_invalid_when_bad_yaml(self, tmp_path, monkeypatch):
        """Should report invalid when config.yaml is invalid YAML."""
        # Clear env vars so get_project_root falls back to cwd
        monkeypatch.delenv("PONGOGO_KNOWLEDGE_PATH", raising=False)
        monkeypatch.delenv("PONGOGO_PROJECT_ROOT", raising=False)
        pongogo_dir = tmp_path / ".pongogo"
        pongogo_dir.mkdir()
        config_path = pongogo_dir / "config.yaml"
        config_path.write_text("invalid: [yaml: syntax")
        monkeypatch.chdir(tmp_path)

        result = check_config_validity()
        assert result["status"] == "invalid"


class TestGetHealthStatus:
    """Tests for get_health_status function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return dictionary with overall status."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "events.db",
        )

        result = get_health_status()
        assert isinstance(result, dict)
        assert "overall" in result

    def test_includes_all_components(self, tmp_path, monkeypatch):
        """Should include all health check components."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "events.db",
        )

        result = get_health_status()
        assert "container" in result
        assert "database" in result
        assert "events" in result
        assert "config" in result
        assert "timestamp" in result

    def test_overall_degraded_when_missing_components(self, tmp_path, monkeypatch):
        """Should report degraded when some components are missing."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "mcp_server.health_check.get_events_db_path",
            lambda: tmp_path / "events.db",
        )

        result = get_health_status()
        # Without config or database, should be degraded or unhealthy
        assert result["overall"] in ("degraded", "unhealthy")
