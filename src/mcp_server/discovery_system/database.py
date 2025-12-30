"""
Discovery System Database - Schema and Connection Management

Provides SQLite database for discovery catalog, tracking knowledge patterns
found in CLAUDE.md, wiki/, and docs/ during pongogo init.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class DiscoveryDatabase:
    """SQLite database for Repository Knowledge Discovery system."""

    SCHEMA_VERSION = 1

    SCHEMA = """
    -- Schema version tracking
    CREATE TABLE IF NOT EXISTS schema_info (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    -- Core discoveries table
    CREATE TABLE IF NOT EXISTS discoveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT NOT NULL,              -- Path to original file (relative to project root)
        source_type TEXT NOT NULL,              -- CLAUDE_MD, WIKI, DOCS
        section_title TEXT,                     -- Extracted section heading
        section_content TEXT NOT NULL,          -- Raw content of the section
        content_hash TEXT NOT NULL,             -- SHA-256 for change detection
        keywords TEXT,                          -- JSON array of extracted keywords
        status TEXT NOT NULL DEFAULT 'DISCOVERED',  -- DISCOVERED, PROMOTED, ARCHIVED
        instruction_file TEXT,                  -- Path to instruction file if promoted
        discovered_at TEXT NOT NULL,            -- ISO timestamp when discovered
        promoted_at TEXT,                       -- ISO timestamp when promoted (NULL if not)
        archived_at TEXT,                       -- ISO timestamp when archived (NULL if not)
        archive_reason TEXT                     -- Reason for archiving (NULL if not archived)
    );

    -- Scan history for tracking init runs
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_date TEXT NOT NULL,                -- ISO timestamp
        source_type TEXT NOT NULL,              -- CLAUDE_MD, WIKI, DOCS
        files_scanned INTEGER NOT NULL,         -- Number of files processed
        sections_found INTEGER NOT NULL,        -- Number of sections extracted
        new_discoveries INTEGER NOT NULL,       -- New discoveries added
        updated_discoveries INTEGER NOT NULL    -- Existing discoveries updated
    );

    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_discoveries_status ON discoveries(status);
    CREATE INDEX IF NOT EXISTS idx_discoveries_source_type ON discoveries(source_type);
    CREATE INDEX IF NOT EXISTS idx_discoveries_content_hash ON discoveries(content_hash);
    CREATE INDEX IF NOT EXISTS idx_discoveries_discovered_at ON discoveries(discovered_at);
    CREATE INDEX IF NOT EXISTS idx_scan_history_date ON scan_history(scan_date);
    """

    def __init__(self, project_root: Path):
        """
        Initialize database connection.

        Args:
            project_root: Path to project root directory.
                         Database will be created at .pongogo/discovery.db
        """
        self.project_root = Path(project_root)
        self.db_path = self.project_root / ".pongogo" / "discovery.db"
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and schema if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(self.SCHEMA)
            # Set schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION)),
            )

    @contextmanager
    def connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection with row_factory set to sqlite3.Row
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> list:
        """Execute SQL and return all results."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def execute_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute SQL and return first result."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def execute_insert(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT and return last row ID."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """Execute UPDATE/DELETE and return rows affected."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    def get_schema_version(self) -> int:
        """Get current schema version."""
        result = self.execute_one(
            "SELECT value FROM schema_info WHERE key = ?", ("schema_version",)
        )
        return int(result["value"]) if result else 0

    def count_discoveries(self, status: str | None = None) -> int:
        """Count discoveries with optional status filter."""
        if status:
            result = self.execute_one(
                "SELECT COUNT(*) as cnt FROM discoveries WHERE status = ?", (status,)
            )
        else:
            result = self.execute_one("SELECT COUNT(*) as cnt FROM discoveries")
        return result["cnt"] if result else 0

    def count_by_source_type(self) -> dict:
        """Count discoveries grouped by source type."""
        rows = self.execute(
            """
            SELECT source_type, COUNT(*) as cnt
            FROM discoveries
            WHERE status != 'ARCHIVED'
            GROUP BY source_type
            """
        )
        return {row["source_type"]: row["cnt"] for row in rows}

    def get_discovery_by_hash(self, content_hash: str) -> sqlite3.Row | None:
        """Find discovery by content hash (for duplicate detection)."""
        return self.execute_one(
            "SELECT * FROM discoveries WHERE content_hash = ?", (content_hash,)
        )

    def reset(self):
        """Reset database (drop and recreate all tables). USE WITH CAUTION."""
        with self.connection() as conn:
            conn.executescript("""
                DROP TABLE IF EXISTS scan_history;
                DROP TABLE IF EXISTS discoveries;
                DROP TABLE IF EXISTS schema_info;
            """)
        self._ensure_db_exists()
