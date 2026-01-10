"""
Routing event storage and retrieval.

Captures routing events for lookback features, diagnostics, and analysis.
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .database import PongogoDatabase, get_default_db_path

logger = logging.getLogger(__name__)

# Retry configuration for transient database locks
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.05  # 50ms base delay with exponential backoff


def store_routing_event(
    user_message: str,
    routed_instructions: list[str],
    engine_version: str,
    routing_scores: dict[str, int] | None = None,
    context: dict | None = None,
    session_id: str | None = None,
    routing_latency_ms: float | None = None,
    db_path: Path | None = None,
) -> bool:
    """Store a routing event to the database.

    Event capture is non-blocking - failures are logged but don't interrupt
    the routing response. Uses retry with exponential backoff for transient
    database lock errors under high contention.

    Args:
        user_message: The user's query/message
        routed_instructions: List of instruction IDs that were routed
        engine_version: Version of the routing engine (e.g., "durian-0.6.2")
        routing_scores: Optional dict of instruction -> score mappings
        context: Optional context dict (files, directories, branch, etc.)
        session_id: Optional session identifier
        routing_latency_ms: Optional routing computation time in ms
        db_path: Optional explicit database path

    Returns:
        True if event was stored successfully, False otherwise
    """
    timestamp = datetime.now().isoformat()
    message_hash = hashlib.sha256(user_message.encode()).hexdigest()[:16]
    instructions_json = json.dumps(routed_instructions) if routed_instructions else None
    scores_json = json.dumps(routing_scores) if routing_scores else None
    context_json = json.dumps(context) if context else None
    instruction_count = len(routed_instructions) if routed_instructions else 0

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            db = PongogoDatabase(db_path=db_path or get_default_db_path())

            db.execute_insert(
                """
                INSERT INTO routing_events
                (timestamp, user_message, message_hash, routed_instructions,
                 instruction_count, routing_scores, engine_version,
                 session_id, context, routing_latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    user_message,
                    message_hash,
                    instructions_json,
                    instruction_count,
                    scores_json,
                    engine_version,
                    session_id,
                    context_json,
                    routing_latency_ms,
                ),
            )

            logger.debug(f"Routing event captured: {instruction_count} instructions")
            return True

        except sqlite3.OperationalError as e:
            last_error = e
            # Retry on database locked errors
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)  # Exponential backoff
                logger.debug(
                    f"Database locked, retrying in {delay:.3f}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(delay)
                continue
            else:
                logger.warning(
                    f"Failed to store routing event after {attempt + 1} attempts: {e}"
                )
                return False

        except Exception as e:
            logger.warning(f"Failed to store routing event: {e}")
            return False

    logger.warning(
        f"Failed to store routing event after {MAX_RETRIES} attempts: {last_error}"
    )
    return False


def get_event_stats(db_path: Path | None = None) -> dict:
    """Get statistics about captured routing events.

    Used by /pongogo-diagnose and health check tools.

    Args:
        db_path: Optional explicit database path

    Returns:
        Dictionary with event statistics
    """
    path = db_path or get_default_db_path()

    if not path.exists():
        return {
            "status": "missing",
            "total_count": 0,
            "first_event": None,
            "last_event": None,
            "last_24h_count": 0,
            "database_path": str(path),
            "database_exists": False,
        }

    try:
        db = PongogoDatabase(db_path=path)

        # Total count
        result = db.execute_one("SELECT COUNT(*) as cnt FROM routing_events")
        total_count = result["cnt"] if result else 0

        if total_count == 0:
            return {
                "status": "empty",
                "total_count": 0,
                "first_event": None,
                "last_event": None,
                "last_24h_count": 0,
                "database_path": str(path),
                "database_exists": True,
            }

        # First event
        first = db.execute_one(
            "SELECT timestamp FROM routing_events ORDER BY id ASC LIMIT 1"
        )
        first_event = first["timestamp"] if first else None

        # Last event
        last = db.execute_one(
            "SELECT timestamp FROM routing_events ORDER BY id DESC LIMIT 1"
        )
        last_event = last["timestamp"] if last else None

        # Last 24h count
        last_24h = db.execute_one(
            """
            SELECT COUNT(*) as cnt FROM routing_events
            WHERE timestamp > datetime('now', '-1 day')
            """
        )
        last_24h_count = last_24h["cnt"] if last_24h else 0

        # Engine version distribution
        engines = db.execute(
            """
            SELECT engine_version, COUNT(*) as cnt
            FROM routing_events
            GROUP BY engine_version
            ORDER BY cnt DESC
            """
        )
        engine_distribution = {row["engine_version"]: row["cnt"] for row in engines}

        return {
            "status": "active",
            "total_count": total_count,
            "first_event": first_event,
            "last_event": last_event,
            "last_24h_count": last_24h_count,
            "engine_distribution": engine_distribution,
            "database_path": str(path),
            "database_exists": True,
        }

    except Exception as e:
        logger.warning(f"Database error getting stats: {e}")
        return {
            "status": "error",
            "total_count": 0,
            "first_event": None,
            "last_event": None,
            "last_24h_count": 0,
            "database_path": str(path),
            "database_exists": True,
            "error": str(e),
        }


def get_recent_events(
    limit: int = 50,
    session_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Get recent routing events for lookback.

    Args:
        limit: Maximum number of events to return
        session_id: Optional filter by session
        db_path: Optional explicit database path

    Returns:
        List of event dictionaries
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        if session_id:
            rows = db.execute(
                """
                SELECT * FROM routing_events
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            )
        else:
            rows = db.execute(
                """
                SELECT * FROM routing_events
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            )

        return [dict(row) for row in rows]

    except Exception as e:
        logger.warning(f"Failed to get recent events: {e}")
        return []
