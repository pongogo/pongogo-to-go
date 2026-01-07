"""
Routing event capture for pongogo-to-go.

Captures routing events to local SQLite database for:
- Lookback features (learning from past routing)
- Diagnostic information (/pongogo-diagnose)
- Future cloud sync (paid tiers)

Storage: .pongogo/pongogo.db (unified database, schema v3.0.0)

This module provides backward-compatible wrappers around the unified database module.
"""

import logging
from pathlib import Path

from .database import (
    get_default_db_path,
)
from .database import (
    get_event_stats as _get_event_stats,
)
from .database import (
    get_recent_events as _get_recent_events,
)
from .database import (
    store_routing_event as _store_routing_event,
)

logger = logging.getLogger(__name__)


def get_events_db_path() -> Path:
    """Get the path to the events database.

    Returns:
        Path to pongogo.db (unified database)
    """
    return get_default_db_path()


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
    return _store_routing_event(
        user_message=user_message,
        routed_instructions=routed_instructions,
        engine_version=engine_version,
        context=context,
        session_id=session_id,
    )


def get_event_stats() -> dict:
    """Get statistics about captured routing events.

    Used by /pongogo-diagnose and health check tools.

    Returns:
        Dictionary with event statistics:
        - status: "active", "empty", "missing", or "error"
        - total_count: Total number of events
        - first_event: Timestamp of first event (or None)
        - last_event: Timestamp of last event (or None)
        - last_24h_count: Events in the last 24 hours
        - database_path: Path to the database file
        - database_exists: Whether the database file exists
    """
    return _get_event_stats()


def get_recent_events(
    limit: int = 50,
    session_id: str | None = None,
) -> list[dict]:
    """Get recent routing events for lookback.

    Args:
        limit: Maximum number of events to return
        session_id: Optional filter by session

    Returns:
        List of event dictionaries
    """
    return _get_recent_events(limit=limit, session_id=session_id)
