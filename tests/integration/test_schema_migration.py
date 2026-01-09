"""Integration tests for database schema migrations.

Tests that upgrading between schema versions works correctly,
preserving existing data while adding new tables/columns.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from mcp_server.database import PongogoDatabase, SCHEMA_VERSION


class TestSchemaMigration:
    """Tests for schema migration between versions."""

    def test_fresh_install_creates_current_schema(self, tmp_path: Path):
        """Fresh install should create schema at current version."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        assert db.get_schema_version() == SCHEMA_VERSION
        assert db_path.exists()

    def test_schema_version_matches_constant(self, tmp_path: Path):
        """Schema version in DB should match SCHEMA_VERSION constant."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        # Verify the constant is what we expect
        assert SCHEMA_VERSION == "3.1.0"
        assert db.get_schema_version() == "3.1.0"

    def test_upgrade_from_300_preserves_routing_events(self, tmp_path: Path):
        """Upgrading from 3.0.0 should preserve routing_events data."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a minimal 3.0.0 schema (without guidance_fulfillment)
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE schema_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO schema_info (key, value) VALUES ('schema_version', '3.0.0');

            CREATE TABLE routing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                message_hash TEXT,
                routed_instructions TEXT,
                instruction_count INTEGER DEFAULT 0,
                routing_scores TEXT,
                engine_version TEXT DEFAULT 'durian-0.6.1',
                session_id TEXT,
                context TEXT,
                routing_latency_ms REAL,
                exclude_from_eval BOOLEAN DEFAULT 0,
                exclude_reason TEXT
            );

            -- Insert test data
            INSERT INTO routing_events (timestamp, user_message, instruction_count)
            VALUES ('2025-01-01T00:00:00', 'test message 1', 3);
            INSERT INTO routing_events (timestamp, user_message, instruction_count)
            VALUES ('2025-01-02T00:00:00', 'test message 2', 5);
        """)
        conn.commit()
        conn.close()

        # Now open with PongogoDatabase - should upgrade
        db = PongogoDatabase(db_path=db_path)

        # Verify upgrade happened
        assert db.get_schema_version() == "3.1.0"

        # Verify existing data preserved
        events = db.execute("SELECT user_message FROM routing_events ORDER BY id")
        assert len(events) == 2
        assert events[0]["user_message"] == "test message 1"
        assert events[1]["user_message"] == "test message 2"

    def test_upgrade_from_300_creates_guidance_fulfillment(self, tmp_path: Path):
        """Upgrading from 3.0.0 should create guidance_fulfillment table."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create 3.0.0 schema without guidance_fulfillment
        # Must include required columns for indexes to work
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE schema_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO schema_info (key, value) VALUES ('schema_version', '3.0.0');

            -- Tables with required columns for indexes
            CREATE TABLE routing_events (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                engine_version TEXT
            );
            CREATE TABLE routing_triggers (
                id INTEGER PRIMARY KEY,
                trigger_type TEXT,
                enabled BOOLEAN
            );
            CREATE TABLE artifact_discovered (
                id INTEGER PRIMARY KEY,
                status TEXT,
                source_type TEXT
            );
            CREATE TABLE artifact_implemented (
                id INTEGER PRIMARY KEY,
                status TEXT,
                instruction_category TEXT
            );
            CREATE TABLE observation_discovered (
                id INTEGER PRIMARY KEY,
                status TEXT,
                observation_type TEXT
            );
            CREATE TABLE observation_implemented (
                id INTEGER PRIMARY KEY,
                status TEXT,
                implementation_type TEXT
            );
            CREATE TABLE scan_history (
                id INTEGER PRIMARY KEY,
                scan_date TEXT
            );
        """)
        conn.commit()
        conn.close()

        # Open with PongogoDatabase - should upgrade
        db = PongogoDatabase(db_path=db_path)

        # Verify guidance_fulfillment table exists
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='guidance_fulfillment'"
        )
        assert len(tables) == 1
        assert tables[0]["name"] == "guidance_fulfillment"

    def test_guidance_fulfillment_table_structure(self, tmp_path: Path):
        """guidance_fulfillment table should have correct structure."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        # Get table info
        columns = db.execute("PRAGMA table_info(guidance_fulfillment)")
        column_names = {col["name"] for col in columns}

        # Verify expected columns exist
        expected_columns = {
            "id",
            "guidance_event_id",
            "guidance_type",
            "guidance_content",
            "action_type",
            "fulfillment_status",
            "fulfillment_event_id",
            "fulfillment_evidence",
            "distance_to_fulfillment",
            "confidence",
            "session_id",
            "conversation_id",
            "created_at",
            "fulfilled_at",
        }
        assert expected_columns.issubset(column_names)

    def test_guidance_fulfillment_status_constraint(self, tmp_path: Path):
        """guidance_fulfillment should enforce status CHECK constraint."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        # Valid status should work
        db.execute_insert("""
            INSERT INTO guidance_fulfillment
            (guidance_type, guidance_content, action_type, fulfillment_status)
            VALUES ('explicit', 'test content', 'run_tests', 'pending')
        """)

        # Invalid status should fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute_insert("""
                INSERT INTO guidance_fulfillment
                (guidance_type, guidance_content, action_type, fulfillment_status)
                VALUES ('explicit', 'test', 'run_tests', 'invalid_status')
            """)

    def test_idempotent_schema_application(self, tmp_path: Path):
        """Schema application should be idempotent (safe to run multiple times)."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        # Create DB twice
        db1 = PongogoDatabase(db_path=db_path)
        version1 = db1.get_schema_version()

        db2 = PongogoDatabase(db_path=db_path)
        version2 = db2.get_schema_version()

        assert version1 == version2 == SCHEMA_VERSION


class TestDataPreservation:
    """Tests that upgrades preserve existing data."""

    def test_routing_triggers_preserved(self, tmp_path: Path):
        """Routing triggers should survive upgrade."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        # Insert test data
        db.execute_insert("""
            INSERT INTO routing_triggers
            (trigger_type, trigger_key, trigger_value, source)
            VALUES ('friction', 'oops', 'mistake_recovery', 'built_in')
        """)

        # Re-open database (simulates restart)
        db2 = PongogoDatabase(db_path=db_path)

        # Verify data preserved
        triggers = db2.execute(
            "SELECT trigger_key FROM routing_triggers WHERE trigger_type = 'friction'"
        )
        assert len(triggers) == 1
        assert triggers[0]["trigger_key"] == "oops"

    def test_scan_history_preserved(self, tmp_path: Path):
        """Scan history should survive upgrade."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        # Insert test data
        db.execute_insert("""
            INSERT INTO scan_history
            (scan_date, scan_type, source_type, files_scanned)
            VALUES ('2025-01-01', 'full', 'init', 42)
        """)

        # Re-open database
        db2 = PongogoDatabase(db_path=db_path)

        # Verify data preserved
        history = db2.execute("SELECT files_scanned FROM scan_history")
        assert len(history) == 1
        assert history[0]["files_scanned"] == 42
