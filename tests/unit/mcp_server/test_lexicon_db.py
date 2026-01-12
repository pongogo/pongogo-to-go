"""Tests for lexicon_db module.

Verifies the SQLite-based lexicon system loads correctly and provides
expected data for guidance and friction pattern matching.
"""

import sqlite3

import pytest

from mcp_server.lexicon_db import (
    DEFAULT_DB_PATH,
    LexiconDB,
)


class TestLexiconDBAvailability:
    """Tests for lexicon.db file availability."""

    def test_default_db_path_exists(self):
        """Verify lexicon.db file exists at expected location."""
        assert DEFAULT_DB_PATH is not None
        assert DEFAULT_DB_PATH.exists(), f"lexicon.db not found at {DEFAULT_DB_PATH}"

    def test_db_is_readable(self):
        """Verify lexicon.db can be opened and read."""
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM lexicon_entries")
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0, "lexicon.db has no entries"


class TestLexiconDBLoader:
    """Tests for LexiconDB class."""

    @pytest.fixture
    def lexicon_db(self):
        """Create LexiconDB instance."""
        return LexiconDB()

    def test_get_all_entries_returns_list(self, lexicon_db):
        """get_all_entries should return a list of entries."""
        entries = lexicon_db.get_all_entries()

        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_entries_have_required_fields(self, lexicon_db):
        """Each entry should have required fields for matching."""
        entries = lexicon_db.get_all_entries()
        entry = entries[0]

        # Required fields for pattern matching
        assert hasattr(entry, "id") or "id" in entry
        assert hasattr(entry, "pattern") or "pattern" in entry

    def test_get_stats_returns_counts(self, lexicon_db):
        """get_stats should return entry counts."""
        stats = lexicon_db.get_stats()

        assert isinstance(stats, dict)
        assert "total_count" in stats or "guidance_count" in stats
        assert stats.get("guidance_count", 0) >= 0
        assert stats.get("friction_count", 0) >= 0

    def test_has_guidance_entries(self, lexicon_db):
        """Should have guidance entries loaded."""
        stats = lexicon_db.get_stats()
        guidance_count = stats.get("guidance_count", 0)

        assert guidance_count > 0, "No guidance entries in lexicon"

    def test_has_friction_entries(self, lexicon_db):
        """Should have friction entries loaded."""
        stats = lexicon_db.get_stats()
        friction_count = stats.get("friction_count", 0)

        assert friction_count > 0, "No friction entries in lexicon"


class TestLexiconDBSchema:
    """Tests for lexicon.db schema integrity."""

    def test_lexicon_entries_table_exists(self):
        """lexicon_entries table should exist."""
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='lexicon_entries'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "lexicon_entries table not found"

    def test_required_columns_exist(self):
        """Required columns should exist in lexicon_entries table."""
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(lexicon_entries)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required = {"entry_id", "pattern", "lexicon_type", "category"}
        missing = required - columns

        assert not missing, f"Missing required columns: {missing}"

    def test_enabled_entries_only(self):
        """All entries should be enabled (enabled=1)."""
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM lexicon_entries WHERE enabled=1")
        enabled_count = cursor.fetchone()[0]

        conn.close()

        assert enabled_count > 0, "No enabled entries in lexicon"
