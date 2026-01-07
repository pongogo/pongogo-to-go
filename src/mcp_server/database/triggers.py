"""
Routing trigger management.

Manages dictionaries for friction patterns, guidance detection, and violation patterns.
"""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from .database import PongogoDatabase, get_default_db_path

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Types of routing triggers."""

    FRICTION = "FRICTION"  # Patterns indicating friction/mistakes
    GUIDANCE_EXPLICIT = "GUIDANCE_EXPLICIT"  # Explicit user directives
    GUIDANCE_IMPLICIT = "GUIDANCE_IMPLICIT"  # Implicit preferences/wishes
    VIOLATION = "VIOLATION"  # Policy violation patterns


def get_triggers_by_type(
    trigger_type: TriggerType,
    enabled_only: bool = True,
    db_path: Path | None = None,
) -> dict[str, str | None]:
    """Get all triggers of a specific type.

    Args:
        trigger_type: Type of triggers to retrieve
        enabled_only: Only return enabled triggers
        db_path: Optional explicit database path

    Returns:
        Dictionary mapping trigger_key -> trigger_value
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        if enabled_only:
            rows = db.execute(
                """
                SELECT trigger_key, trigger_value
                FROM routing_triggers
                WHERE trigger_type = ? AND enabled = 1
                """,
                (trigger_type.value,),
            )
        else:
            rows = db.execute(
                """
                SELECT trigger_key, trigger_value
                FROM routing_triggers
                WHERE trigger_type = ?
                """,
                (trigger_type.value,),
            )

        return {row["trigger_key"]: row["trigger_value"] for row in rows}

    except Exception as e:
        logger.warning(f"Failed to get triggers: {e}")
        return {}


def upsert_trigger(
    trigger_type: TriggerType,
    trigger_key: str,
    trigger_value: str | None = None,
    category: str | None = None,
    description: str | None = None,
    source: str = "built_in",
    confidence: str = "HIGH",
    enabled: bool = True,
    created_by: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Insert or update a trigger.

    Args:
        trigger_type: Type of trigger
        trigger_key: The pattern/phrase to detect
        trigger_value: Associated action/instruction
        category: Grouping category
        description: Human-readable explanation
        source: Origin (built_in, learned, user_defined)
        confidence: Confidence level (HIGH, MEDIUM, LOW)
        enabled: Whether trigger is active
        created_by: Who created this trigger
        db_path: Optional explicit database path

    Returns:
        Row ID of inserted/updated trigger
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())
        now = datetime.now().isoformat()

        # Try insert first, update if conflict
        row_id = db.execute_insert(
            """
            INSERT INTO routing_triggers
            (trigger_type, trigger_key, trigger_value, category, description,
             source, confidence, enabled, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trigger_type, trigger_key) DO UPDATE SET
                trigger_value = excluded.trigger_value,
                category = excluded.category,
                description = excluded.description,
                source = excluded.source,
                confidence = excluded.confidence,
                enabled = excluded.enabled,
                updated_at = excluded.updated_at
            """,
            (
                trigger_type.value,
                trigger_key,
                trigger_value,
                category,
                description,
                source,
                confidence,
                enabled,
                created_by,
                now,
                now,
            ),
        )

        logger.debug(f"Upserted trigger: {trigger_type.value}/{trigger_key}")
        return row_id

    except Exception as e:
        logger.warning(f"Failed to upsert trigger: {e}")
        return 0


def bulk_load_triggers(
    trigger_type: TriggerType,
    triggers: dict[str, str | None],
    source: str = "built_in",
    replace_existing: bool = False,
    db_path: Path | None = None,
) -> int:
    """Bulk load triggers from a dictionary.

    Used to initialize triggers from router.py FRICTION_PATTERNS, etc.

    Args:
        trigger_type: Type of triggers
        triggers: Dictionary of trigger_key -> trigger_value
        source: Origin of these triggers
        replace_existing: If True, disable existing triggers of this type
        db_path: Optional explicit database path

    Returns:
        Number of triggers loaded
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        if replace_existing:
            db.execute_update(
                """
                UPDATE routing_triggers
                SET enabled = 0, updated_at = ?
                WHERE trigger_type = ? AND source = ?
                """,
                (datetime.now().isoformat(), trigger_type.value, source),
            )

        count = 0
        for key, value in triggers.items():
            upsert_trigger(
                trigger_type=trigger_type,
                trigger_key=key,
                trigger_value=value,
                source=source,
                db_path=db_path,
            )
            count += 1

        logger.info(f"Loaded {count} {trigger_type.value} triggers")
        return count

    except Exception as e:
        logger.warning(f"Failed to bulk load triggers: {e}")
        return 0


def get_trigger_stats(db_path: Path | None = None) -> dict:
    """Get trigger statistics.

    Returns:
        Dictionary with trigger counts by type and source
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Count by type
        by_type = db.execute(
            """
            SELECT trigger_type, COUNT(*) as total,
                   SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled
            FROM routing_triggers
            GROUP BY trigger_type
            """
        )

        # Count by source
        by_source = db.execute(
            """
            SELECT source, COUNT(*) as cnt
            FROM routing_triggers
            WHERE enabled = 1
            GROUP BY source
            """
        )

        return {
            "by_type": {
                row["trigger_type"]: {"total": row["total"], "enabled": row["enabled"]}
                for row in by_type
            },
            "by_source": {row["source"]: row["cnt"] for row in by_source},
        }

    except Exception as e:
        logger.warning(f"Failed to get trigger stats: {e}")
        return {"by_type": {}, "by_source": {}}
