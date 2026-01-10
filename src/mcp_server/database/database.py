"""
Core database connection and schema management for Pongogo Unified Database.

The unified database consolidates:
- routing_events (event logging)
- artifact_* tables (file-based knowledge lifecycle)
- routing_triggers (friction/guidance dictionaries)
- observation_* tables (runtime observation lifecycle)

Location: .pongogo/pongogo.db (project root)
Fallback: ~/.pongogo/pongogo.db (user-level)
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# Schema version for migrations
SCHEMA_VERSION = "3.1.0"  # Phase 9: Added guidance_fulfillment table


def get_default_db_path(project_root: Path | None = None) -> Path:
    """Get the default database path.

    Path resolution:
    1. If project_root provided: .pongogo/pongogo.db (project-local)
    2. Otherwise: ~/.pongogo/pongogo.db (user-level fallback)

    Args:
        project_root: If provided, uses project-local database.

    Returns:
        Path to pongogo.db
    """
    if project_root:
        return Path(project_root) / ".pongogo" / "pongogo.db"
    else:
        # User-level fallback
        return Path.home() / ".pongogo" / "pongogo.db"


# Embedded schema (unified v3.0.0)
SCHEMA = """
-- Schema metadata
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Routing events (core event logging)
CREATE TABLE IF NOT EXISTS routing_events (
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

CREATE INDEX IF NOT EXISTS idx_routing_events_timestamp ON routing_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_routing_events_session ON routing_events(session_id);
CREATE INDEX IF NOT EXISTS idx_routing_events_engine ON routing_events(engine_version);

-- Routing triggers (friction, guidance, violation dictionaries)
CREATE TABLE IF NOT EXISTS routing_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,
    trigger_key TEXT NOT NULL,
    trigger_value TEXT,
    category TEXT,
    description TEXT,
    source TEXT NOT NULL DEFAULT 'built_in',
    confidence TEXT DEFAULT 'HIGH',
    enabled BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    UNIQUE(trigger_type, trigger_key)
);

CREATE INDEX IF NOT EXISTS idx_triggers_type ON routing_triggers(trigger_type);
CREATE INDEX IF NOT EXISTS idx_triggers_enabled ON routing_triggers(enabled);

-- Artifact discovered (file-based knowledge from repo)
CREATE TABLE IF NOT EXISTS artifact_discovered (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    source_type TEXT NOT NULL,
    section_title TEXT,
    section_content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    keywords TEXT,
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    promoted_to INTEGER,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at TEXT,
    archived_at TEXT,
    archive_reason TEXT,
    UNIQUE(content_hash)
);

CREATE INDEX IF NOT EXISTS idx_artifact_discovered_status ON artifact_discovered(status);
CREATE INDEX IF NOT EXISTS idx_artifact_discovered_source_type ON artifact_discovered(source_type);

-- Artifact implemented (promoted to instruction files)
CREATE TABLE IF NOT EXISTS artifact_implemented (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovered_id INTEGER,
    instruction_file TEXT NOT NULL,
    instruction_id TEXT,
    instruction_category TEXT,
    content_hash TEXT NOT NULL,
    word_count INTEGER,
    title TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TEXT,
    deprecated_reason TEXT,
    times_routed INTEGER DEFAULT 0,
    avg_routing_score REAL,
    FOREIGN KEY (discovered_id) REFERENCES artifact_discovered(id)
);

CREATE INDEX IF NOT EXISTS idx_artifact_implemented_status ON artifact_implemented(status);
CREATE INDEX IF NOT EXISTS idx_artifact_implemented_category ON artifact_implemented(instruction_category);

-- Observation discovered (runtime guidance/patterns)
CREATE TABLE IF NOT EXISTS observation_discovered (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    observation_type TEXT NOT NULL,
    observation_content TEXT NOT NULL,
    observation_target TEXT,
    guidance_type TEXT,
    should_persist BOOLEAN DEFAULT 1,
    persistence_scope TEXT DEFAULT 'project',
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    promoted_to INTEGER,
    session_id TEXT,
    context TEXT,
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    promoted_at TEXT,
    rejected_at TEXT,
    rejection_reason TEXT,
    FOREIGN KEY (event_id) REFERENCES routing_events(id)
);

CREATE INDEX IF NOT EXISTS idx_observation_discovered_status ON observation_discovered(status);
CREATE INDEX IF NOT EXISTS idx_observation_discovered_type ON observation_discovered(observation_type);

-- Observation implemented (promoted to triggers/instructions/rules)
CREATE TABLE IF NOT EXISTS observation_implemented (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovered_id INTEGER,
    implementation_type TEXT NOT NULL,
    trigger_id INTEGER,
    instruction_id INTEGER,
    rule_content TEXT,
    rule_scope TEXT,
    title TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TEXT,
    deprecated_reason TEXT,
    times_applied INTEGER DEFAULT 0,
    feedback_positive INTEGER DEFAULT 0,
    feedback_negative INTEGER DEFAULT 0,
    FOREIGN KEY (discovered_id) REFERENCES observation_discovered(id),
    FOREIGN KEY (trigger_id) REFERENCES routing_triggers(id),
    FOREIGN KEY (instruction_id) REFERENCES artifact_implemented(id)
);

CREATE INDEX IF NOT EXISTS idx_observation_implemented_status ON observation_implemented(status);
CREATE INDEX IF NOT EXISTS idx_observation_implemented_type ON observation_implemented(implementation_type);

-- Scan history (pongogo init runs)
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date TEXT NOT NULL,
    scan_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    files_scanned INTEGER DEFAULT 0,
    sections_found INTEGER DEFAULT 0,
    new_discoveries INTEGER DEFAULT 0,
    updated_discoveries INTEGER DEFAULT 0,
    duration_ms INTEGER,
    engine_version TEXT,
    pongogo_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_scan_history_date ON scan_history(scan_date);

-- Guidance fulfillment tracking (Phase 9, Issue #390)
-- Tracks whether guidance given in message N is operationalized in subsequent messages
CREATE TABLE IF NOT EXISTS guidance_fulfillment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The guidance event
    guidance_event_id INTEGER,
    guidance_type TEXT NOT NULL,
    guidance_content TEXT NOT NULL,
    action_type TEXT NOT NULL,

    -- Fulfillment tracking
    fulfillment_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(fulfillment_status IN ('pending', 'in_progress', 'fulfilled', 'abandoned', 'superseded')),

    -- Evidence
    fulfillment_event_id INTEGER,
    fulfillment_evidence TEXT,
    distance_to_fulfillment INTEGER,
    confidence REAL DEFAULT 0.0,

    -- Session context
    session_id TEXT,
    conversation_id TEXT,

    -- Timing
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at TEXT,

    FOREIGN KEY (guidance_event_id) REFERENCES routing_events(id),
    FOREIGN KEY (fulfillment_event_id) REFERENCES routing_events(id)
);

CREATE INDEX IF NOT EXISTS idx_guidance_fulfillment_status ON guidance_fulfillment(fulfillment_status);
CREATE INDEX IF NOT EXISTS idx_guidance_fulfillment_session ON guidance_fulfillment(session_id);
CREATE INDEX IF NOT EXISTS idx_guidance_fulfillment_action ON guidance_fulfillment(action_type);
"""


class PongogoDatabase:
    """Unified database for all Pongogo routing data."""

    def __init__(
        self, db_path: Path | str | None = None, project_root: Path | None = None
    ):
        """Initialize database connection.

        Args:
            db_path: Explicit path to database file.
            project_root: Project root for project-local database.
                         Ignored if db_path is provided.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_default_db_path(project_root)

        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create database and schema if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connection() as conn:
            conn.executescript(SCHEMA)
            # Set schema version
            conn.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("schema_version", SCHEMA_VERSION),
            )
            conn.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("schema_created_at", "datetime('now')"),
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections.

        Yields:
            sqlite3.Connection with row_factory set to sqlite3.Row
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrent access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
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
            return cursor.lastrowid or 0

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """Execute UPDATE/DELETE and return rows affected."""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    def get_schema_version(self) -> str:
        """Get current schema version."""
        result = self.execute_one(
            "SELECT value FROM schema_info WHERE key = ?", ("schema_version",)
        )
        return result["value"] if result else "unknown"

    def get_stats(self) -> dict:
        """Get database statistics for diagnostics."""
        stats = {
            "schema_version": self.get_schema_version(),
            "database_path": str(self.db_path),
            "database_exists": self.db_path.exists(),
        }

        if not self.db_path.exists():
            return stats

        try:
            # Count rows in each table
            tables = [
                "routing_events",
                "routing_triggers",
                "artifact_discovered",
                "artifact_implemented",
                "observation_discovered",
                "observation_implemented",
            ]

            for table in tables:
                result = self.execute_one(f"SELECT COUNT(*) as cnt FROM {table}")
                stats[f"{table}_count"] = result["cnt"] if result else 0

            # Database file size
            stats["database_size_bytes"] = self.db_path.stat().st_size

        except sqlite3.OperationalError as e:
            stats["error"] = str(e)

        return stats
