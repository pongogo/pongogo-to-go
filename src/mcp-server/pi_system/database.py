"""
PI System Database - Schema and Connection Management

Provides SQLite database for PI metadata, evidence, and relationships.
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "docs" / "project_management" / "potential_improvements.db"


class PIDatabase:
    """SQLite database for Potential Improvements system."""

    SCHEMA_VERSION = 2  # v2: Added classification_reason, classification_model, classification_date

    SCHEMA = """
    -- Schema version tracking
    CREATE TABLE IF NOT EXISTS schema_info (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    -- Core PI metadata
    CREATE TABLE IF NOT EXISTS potential_improvements (
        id TEXT PRIMARY KEY,                    -- PI-001, PI-002, etc.
        title TEXT NOT NULL,
        summary TEXT,
        status TEXT NOT NULL DEFAULT 'CANDIDATE',
        confidence TEXT NOT NULL DEFAULT 'LOW',
        classification TEXT,                     -- CORRECTIVE, EXPLORATORY
        classification_reason TEXT,              -- Why this classification was chosen
        classification_model TEXT,               -- Which model made the classification
        classification_date TEXT,                -- When classification was made
        cluster TEXT,                            -- Domain cluster
        identified_date TEXT,
        last_updated TEXT,
        occurrence_count INTEGER DEFAULT 1,
        source_task TEXT,                        -- Task that identified this PI
        file_path TEXT,                          -- Path to detailed markdown file
        archived INTEGER DEFAULT 0              -- Soft delete flag
    );

    -- Evidence accumulation (each occurrence)
    CREATE TABLE IF NOT EXISTS pi_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pi_id TEXT NOT NULL,
        date TEXT NOT NULL,
        source TEXT NOT NULL,                    -- , RCA-2025-11-15, etc.
        description TEXT,
        FOREIGN KEY (pi_id) REFERENCES potential_improvements(id) ON DELETE CASCADE
    );

    -- N-to-N relationships between PIs
    CREATE TABLE IF NOT EXISTS pi_relationships (
        pi_id_1 TEXT NOT NULL,
        pi_id_2 TEXT NOT NULL,
        relationship_type TEXT NOT NULL,         -- OVERLAPS, SUPERSEDES, BLOCKS, RELATED, DUPLICATE
        notes TEXT,
        discovered_date TEXT,
        PRIMARY KEY (pi_id_1, pi_id_2, relationship_type),
        FOREIGN KEY (pi_id_1) REFERENCES potential_improvements(id) ON DELETE CASCADE,
        FOREIGN KEY (pi_id_2) REFERENCES potential_improvements(id) ON DELETE CASCADE
    );

    -- Implementation tracking
    CREATE TABLE IF NOT EXISTS pi_implementations (
        pi_id TEXT PRIMARY KEY,
        implementation_date TEXT,
        implementation_type TEXT,                -- PATTERN_LIBRARY, INSTRUCTION_FILE, PROCESS_DOC, CODE
        location TEXT,                           -- Where implemented (file path, wiki page, etc.)
        notes TEXT,
        FOREIGN KEY (pi_id) REFERENCES potential_improvements(id) ON DELETE CASCADE
    );

    -- Indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_pi_status ON potential_improvements(status);
    CREATE INDEX IF NOT EXISTS idx_pi_confidence ON potential_improvements(confidence);
    CREATE INDEX IF NOT EXISTS idx_pi_classification ON potential_improvements(classification);
    CREATE INDEX IF NOT EXISTS idx_pi_cluster ON potential_improvements(cluster);
    CREATE INDEX IF NOT EXISTS idx_pi_archived ON potential_improvements(archived);
    CREATE INDEX IF NOT EXISTS idx_evidence_pi_id ON pi_evidence(pi_id);
    CREATE INDEX IF NOT EXISTS idx_evidence_date ON pi_evidence(date);
    CREATE INDEX IF NOT EXISTS idx_relationships_type ON pi_relationships(relationship_type);
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to docs/project_management/potential_improvements.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and schema if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(self.SCHEMA)
            # Set schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION))
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

    def execute_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute SQL and return first result."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def execute_many(self, sql: str, params_list: list) -> int:
        """Execute SQL for multiple parameter sets, return rows affected."""
        with self.connection() as conn:
            cursor = conn.executemany(sql, params_list)
            return cursor.rowcount

    def get_schema_version(self) -> int:
        """Get current schema version."""
        result = self.execute_one("SELECT value FROM schema_info WHERE key = ?", ("schema_version",))
        return int(result["value"]) if result else 0

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.execute_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return result is not None

    def count(self, table_name: str, where: str = "", params: tuple = ()) -> int:
        """Count rows in a table with optional WHERE clause."""
        sql = f"SELECT COUNT(*) as cnt FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        result = self.execute_one(sql, params)
        return result["cnt"] if result else 0

    def reset(self):
        """Reset database (drop and recreate all tables). USE WITH CAUTION."""
        with self.connection() as conn:
            conn.executescript("""
                DROP TABLE IF EXISTS pi_implementations;
                DROP TABLE IF EXISTS pi_relationships;
                DROP TABLE IF EXISTS pi_evidence;
                DROP TABLE IF EXISTS potential_improvements;
                DROP TABLE IF EXISTS schema_info;
            """)
        self._ensure_db_exists()
