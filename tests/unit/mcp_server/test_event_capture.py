"""Tests for event_capture module (backward-compatibility wrapper)."""

from pathlib import Path

from mcp_server.event_capture import (
    get_event_stats,
    get_events_db_path,
    get_recent_events,
    store_routing_event,
)


class TestGetEventsDbPath:
    """Tests for get_events_db_path function."""

    def test_returns_path(self):
        """Path should be returned."""
        path = get_events_db_path()
        assert isinstance(path, Path)

    def test_filename_is_pongogo_db(self):
        """Filename should be pongogo.db (unified database)."""
        path = get_events_db_path()
        assert path.name == "pongogo.db"


class TestStoreRoutingEvent:
    """Tests for store_routing_event function."""

    def test_returns_true_on_success(self, tmp_path, monkeypatch):
        """Should return True when event is stored."""
        # Use temp database - patch at events module level where it's imported
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        result = store_routing_event(
            user_message="test query",
            routed_instructions=["inst1", "inst2"],
            engine_version="test-0.1",
        )
        assert result is True

    def test_stores_event_data(self, tmp_path, monkeypatch):
        """Should store event data in database."""
        import sqlite3

        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        store_routing_event(
            user_message="how do I create an epic?",
            routed_instructions=["epic_management", "task_basics"],
            engine_version="durian-0.6.1",
            context={"branch": "main"},
            session_id="test-session",
        )

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM routing_events")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["user_message"] == "how do I create an epic?"
        assert row["engine_version"] == "durian-0.6.1"
        assert row["instruction_count"] == 2

    def test_handles_empty_instructions(self, tmp_path, monkeypatch):
        """Should handle empty instruction list."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        result = store_routing_event(
            user_message="unrelated query",
            routed_instructions=[],
            engine_version="test-0.1",
        )
        assert result is True


class TestGetEventStats:
    """Tests for get_event_stats function."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return dictionary."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        stats = get_event_stats()
        assert isinstance(stats, dict)

    def test_reports_missing_when_no_db(self, tmp_path, monkeypatch):
        """Should report status=missing when database doesn't exist."""
        # Point to non-existent path that won't be auto-created
        db_path = tmp_path / "nonexistent" / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        stats = get_event_stats()
        assert stats["status"] == "missing"
        assert stats["total_count"] == 0
        assert stats["database_exists"] is False

    def test_counts_events(self, tmp_path, monkeypatch):
        """Should count stored events."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Store some events
        store_routing_event("query 1", ["inst1"], "test-0.1")
        store_routing_event("query 2", ["inst2"], "test-0.1")
        store_routing_event("query 3", ["inst3"], "test-0.1")

        stats = get_event_stats()
        assert stats["total_count"] == 3
        assert stats["database_exists"] is True
        assert stats["status"] == "active"

    def test_includes_database_path(self, tmp_path, monkeypatch):
        """Should include database path in stats."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        # Need to store at least one event to create the DB
        store_routing_event("test", ["inst"], "test-0.1")

        stats = get_event_stats()
        assert stats["database_path"] == str(db_path)


class TestGetRecentEvents:
    """Tests for get_recent_events function."""

    def test_returns_list(self, tmp_path, monkeypatch):
        """Should return a list."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        events = get_recent_events()
        assert isinstance(events, list)

    def test_returns_stored_events(self, tmp_path, monkeypatch):
        """Should return stored events."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        store_routing_event("query 1", ["inst1"], "test-0.1")
        store_routing_event("query 2", ["inst2"], "test-0.1")

        events = get_recent_events(limit=10)
        assert len(events) == 2

    def test_respects_limit(self, tmp_path, monkeypatch):
        """Should respect limit parameter."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        monkeypatch.setattr(
            "mcp_server.database.events.get_default_db_path",
            lambda _project_root=None: db_path,
        )

        for i in range(10):
            store_routing_event(f"query {i}", [f"inst{i}"], "test-0.1")

        events = get_recent_events(limit=5)
        assert len(events) == 5
