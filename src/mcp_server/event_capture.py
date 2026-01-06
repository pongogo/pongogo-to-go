"""
Routing event capture for pongogo-to-go.

Captures routing events to local SQLite database for:
- Lookback features (learning from past routing)
- Diagnostic information (/pongogo-diagnose)
- Future cloud sync (paid tiers)

Storage: ~/.pongogo/sync/events.db (AD-017: Local-First State Architecture)
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database location (user's home directory)
DEFAULT_SYNC_DIR = Path.home() / ".pongogo" / "sync"
DEFAULT_DB_PATH = DEFAULT_SYNC_DIR / "events.db"

# Database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS routing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_message TEXT NOT NULL,
    routed_instructions TEXT,  -- JSON array of instruction IDs
    engine_version TEXT,
    context TEXT,              -- JSON context dict
    session_id TEXT,
    instruction_count INTEGER, -- Number of instructions returned
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_routing_events_timestamp
ON routing_events(timestamp);

CREATE INDEX IF NOT EXISTS idx_routing_events_session
ON routing_events(session_id);
"""


def get_events_db_path() -> Path:
    """Get the path to the events database.

    Returns:
        Path to events.db, creating parent directories if needed.
    """
    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure database schema exists.

    Args:
        conn: SQLite connection
    """
    conn.executescript(SCHEMA)
    conn.commit()


def store_routing_event(
    user_message: str,
    routed_instructions: list[str],
    engine_version: str,
    context: dict | None = None,
    session_id: str | None = None,
) -> bool:
    """Store a routing event to the local database.

    Event capture is non-blocking - failures are logged but don't interrupt
    the routing response. This ensures the MCP server remains responsive.

    Args:
        user_message: The user's query/message
        routed_instructions: List of instruction IDs that were routed
        engine_version: Version of the routing engine (e.g., "durian-0.6.1")
        context: Optional context dict (files, directories, branch, etc.)
        session_id: Optional session identifier

    Returns:
        True if event was stored successfully, False otherwise
    """
    try:
        db_path = get_events_db_path()
        conn = sqlite3.connect(db_path, timeout=5.0)

        # Ensure schema exists (idempotent)
        ensure_schema(conn)

        # Prepare event data
        timestamp = datetime.now().isoformat()
        instructions_json = (
            json.dumps(routed_instructions) if routed_instructions else None
        )
        context_json = json.dumps(context) if context else None
        instruction_count = len(routed_instructions) if routed_instructions else 0

        # Insert event
        conn.execute(
            """
            INSERT INTO routing_events
            (timestamp, user_message, routed_instructions, engine_version,
             context, session_id, instruction_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                user_message,
                instructions_json,
                engine_version,
                context_json,
                session_id,
                instruction_count,
            ),
        )
        conn.commit()
        conn.close()

        logger.debug(f"Routing event captured: {instruction_count} instructions")
        return True

    except Exception as e:
        # Non-blocking - log warning but don't fail the routing request
        logger.warning(f"Failed to store routing event: {e}")
        return False


def get_event_stats() -> dict:
    """Get statistics about captured routing events.

    Used by /pongogo-diagnose and health check tools.

    Returns:
        Dictionary with event statistics:
        - total_count: Total number of events
        - first_event: Timestamp of first event (or None)
        - last_event: Timestamp of last event (or None)
        - last_24h_count: Events in the last 24 hours
        - database_path: Path to the database file
        - database_exists: Whether the database file exists
    """
    db_path = get_events_db_path()

    if not db_path.exists():
        return {
            "total_count": 0,
            "first_event": None,
            "last_event": None,
            "last_24h_count": 0,
            "database_path": str(db_path),
            "database_exists": False,
        }

    try:
        conn = sqlite3.connect(db_path, timeout=5.0)

        # Total count
        total_count = conn.execute("SELECT COUNT(*) FROM routing_events").fetchone()[0]

        # First event
        first_event = conn.execute(
            "SELECT timestamp FROM routing_events ORDER BY id ASC LIMIT 1"
        ).fetchone()
        first_event = first_event[0] if first_event else None

        # Last event
        last_event = conn.execute(
            "SELECT timestamp FROM routing_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_event = last_event[0] if last_event else None

        # Last 24h count
        last_24h_count = conn.execute(
            """
            SELECT COUNT(*) FROM routing_events
            WHERE timestamp > datetime('now', '-1 day')
            """
        ).fetchone()[0]

        conn.close()

        return {
            "total_count": total_count,
            "first_event": first_event,
            "last_event": last_event,
            "last_24h_count": last_24h_count,
            "database_path": str(db_path),
            "database_exists": True,
        }

    except sqlite3.OperationalError as e:
        logger.warning(f"Database error getting stats: {e}")
        return {
            "total_count": 0,
            "first_event": None,
            "last_event": None,
            "last_24h_count": 0,
            "database_path": str(db_path),
            "database_exists": True,
            "error": str(e),
        }
