"""Tests for event_capture module."""

import sqlite3
from pathlib import Path

import pytest

from mcp_server.event_capture import (
    DEFAULT_SYNC_DIR,
    SCHEMA,
    ensure_schema,
    get_event_stats,
    get_events_db_path,
    store_routing_event,
)


class TestGetEventsDbPath:
    """Tests for get_events_db_path function."""

    def test_returns_path(self):
        """Path should be returned."""
        path = get_events_db_path()
        assert isinstance(path, Path)

    def test_path_in_sync_dir(self):
        """Path should be in sync directory."""
        path = get_events_db_path()
        assert path.parent == DEFAULT_SYNC_DIR

    def test_filename_is_events_db(self):
        """Filename should be events.db."""
        path = get_events_db_path()
        assert path.name == "events.db"


class TestEnsureSchema:
    """Tests for ensure_schema function."""

    def test_creates_table(self, tmp_path):
        """Should create routing_events table."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        ensure_schema(conn)

        # Check table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='routing_events'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self, tmp_path):
        """Should be safe to call multiple times."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        ensure_schema(conn)
        ensure_schema(conn)  # Should not raise
        conn.close()


class TestStoreRoutingEvent:
    """Tests for store_routing_event function."""

    def test_returns_true_on_success(self, tmp_path, monkeypatch):
        """Should return True when event is stored."""
        # Use temp database
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            tmp_path / "events.db",
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        result = store_routing_event(
            user_message="test query",
            routed_instructions=["inst1", "inst2"],
            engine_version="test-0.1",
        )
        assert result is True

    def test_stores_event_data(self, tmp_path, monkeypatch):
        """Should store event data in database."""
        db_path = tmp_path / "events.db"
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            db_path,
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        store_routing_event(
            user_message="how do I create an epic?",
            routed_instructions=["epic_management", "task_basics"],
            engine_version="durian-0.6.1",
            context={"branch": "main"},
            session_id="test-session",
        )

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT * FROM routing_events")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        # Check user_message (index 2)
        assert row[2] == "how do I create an epic?"
        # Check engine_version (index 4)
        assert row[4] == "durian-0.6.1"
        # Check instruction_count (index 7)
        assert row[7] == 2

    def test_handles_empty_instructions(self, tmp_path, monkeypatch):
        """Should handle empty instruction list."""
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            tmp_path / "events.db",
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
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
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            tmp_path / "events.db",
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        stats = get_event_stats()
        assert isinstance(stats, dict)

    def test_reports_zero_when_no_events(self, tmp_path, monkeypatch):
        """Should report zero events when database is empty."""
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            tmp_path / "events.db",
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        stats = get_event_stats()
        assert stats["total_count"] == 0
        assert stats["database_exists"] is False

    def test_counts_events(self, tmp_path, monkeypatch):
        """Should count stored events."""
        db_path = tmp_path / "events.db"
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            db_path,
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        # Store some events
        store_routing_event("query 1", ["inst1"], "test-0.1")
        store_routing_event("query 2", ["inst2"], "test-0.1")
        store_routing_event("query 3", ["inst3"], "test-0.1")

        stats = get_event_stats()
        assert stats["total_count"] == 3
        assert stats["database_exists"] is True

    def test_includes_database_path(self, tmp_path, monkeypatch):
        """Should include database path in stats."""
        db_path = tmp_path / "events.db"
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_DB_PATH",
            db_path,
        )
        monkeypatch.setattr(
            "mcp_server.event_capture.DEFAULT_SYNC_DIR",
            tmp_path,
        )

        stats = get_event_stats()
        assert stats["database_path"] == str(db_path)
