"""
Observation discovery and implementation lifecycle.

Manages runtime observations from user interactions:
- Explicit guidance (directives, rules)
- Implicit guidance (wishes, preferences, style)
- Corrections (feedback, fixes)
- Patterns (recurring behaviors)

Lifecycle: DISCOVERED → REVIEWING → PROMOTED/REJECTED → (optionally) ARCHIVED
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from .database import PongogoDatabase, get_default_db_path

logger = logging.getLogger(__name__)


class ObservationType(str, Enum):
    """Types of runtime observations."""

    GUIDANCE_EXPLICIT = "GUIDANCE_EXPLICIT"  # Direct user directives
    GUIDANCE_IMPLICIT = "GUIDANCE_IMPLICIT"  # Inferred preferences
    CORRECTION = "CORRECTION"  # User corrections/feedback
    PATTERN = "PATTERN"  # Recurring behavior patterns


class GuidanceType(str, Enum):
    """Guidance type taxonomy."""

    NONE = "none"
    EXPLICIT = "explicit"
    IMPLICIT_WISH = "implicit_wish"
    IMPLICIT_PREFERENCE = "implicit_preference"
    IMPLICIT_RULE = "implicit_rule"
    CORRECTION_SIGNAL = "correction_signal"
    STYLE_SIGNAL = "style_signal"


class ObservationStatus(str, Enum):
    """Status in observation lifecycle."""

    DISCOVERED = "DISCOVERED"
    REVIEWING = "REVIEWING"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ImplementationType(str, Enum):
    """How an observation was implemented."""

    TRIGGER = "TRIGGER"  # Added to routing_triggers
    INSTRUCTION = "INSTRUCTION"  # Created instruction file
    PROJECT_RULE = "PROJECT_RULE"  # Stored as project-level rule


def store_observation(
    observation_type: ObservationType,
    observation_content: str,
    event_id: int | None = None,
    observation_target: str | None = None,
    guidance_type: GuidanceType | None = None,
    should_persist: bool = True,
    persistence_scope: str = "project",
    session_id: str | None = None,
    context: dict | None = None,
    db_path: Path | None = None,
) -> int:
    """Store a newly discovered observation.

    Args:
        observation_type: Type of observation
        observation_content: The detected guidance/pattern
        event_id: Optional link to routing_events.id
        observation_target: What it applies to
        guidance_type: Guidance taxonomy classification
        should_persist: Whether to make permanent
        persistence_scope: session, project, or global
        session_id: Session identifier
        context: Additional context dict
        db_path: Optional explicit database path

    Returns:
        Row ID of created observation
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        context_json = json.dumps(context) if context else None
        guidance_value = guidance_type.value if guidance_type else None

        row_id = db.execute_insert(
            """
            INSERT INTO observation_discovered
            (event_id, observation_type, observation_content, observation_target,
             guidance_type, should_persist, persistence_scope, status,
             session_id, context, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                observation_type.value,
                observation_content,
                observation_target,
                guidance_value,
                should_persist,
                persistence_scope,
                ObservationStatus.DISCOVERED.value,
                session_id,
                context_json,
                datetime.now().isoformat(),
            ),
        )

        logger.debug(f"Stored observation: {observation_type.value}")
        return row_id

    except Exception as e:
        logger.warning(f"Failed to store observation: {e}")
        return 0


def promote_observation(
    discovered_id: int,
    implementation_type: ImplementationType,
    trigger_id: int | None = None,
    instruction_id: int | None = None,
    rule_content: str | None = None,
    rule_scope: str | None = None,
    title: str | None = None,
    description: str | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Promote an observation to implementation.

    Args:
        discovered_id: ID of observation_discovered record
        implementation_type: How to implement (TRIGGER, INSTRUCTION, PROJECT_RULE)
        trigger_id: Link to routing_triggers.id (if TRIGGER)
        instruction_id: Link to artifact_implemented.id (if INSTRUCTION)
        rule_content: Rule content (if PROJECT_RULE)
        rule_scope: Rule scope (if PROJECT_RULE)
        title: Human-readable title
        description: Brief description
        db_path: Optional explicit database path

    Returns:
        Row ID of observation_implemented record
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Verify discovered observation exists
        discovered = db.execute_one(
            "SELECT * FROM observation_discovered WHERE id = ?",
            (discovered_id,),
        )
        if not discovered:
            logger.warning(f"Observation not found: {discovered_id}")
            return None

        now = datetime.now().isoformat()

        # Create implemented record
        impl_id = db.execute_insert(
            """
            INSERT INTO observation_implemented
            (discovered_id, implementation_type, trigger_id, instruction_id,
             rule_content, rule_scope, title, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                discovered_id,
                implementation_type.value,
                trigger_id,
                instruction_id,
                rule_content,
                rule_scope,
                title,
                description,
                "ACTIVE",
                now,
            ),
        )

        # Update discovered record
        db.execute_update(
            """
            UPDATE observation_discovered
            SET status = ?, promoted_to = ?, promoted_at = ?
            WHERE id = ?
            """,
            (ObservationStatus.PROMOTED.value, impl_id, now, discovered_id),
        )

        logger.info(
            f"Promoted observation {discovered_id} as {implementation_type.value}"
        )
        return impl_id

    except Exception as e:
        logger.warning(f"Failed to promote observation: {e}")
        return None


def reject_observation(
    observation_id: int,
    reason: str,
    db_path: Path | None = None,
) -> bool:
    """Reject an observation (not worth implementing).

    Args:
        observation_id: ID of observation to reject
        reason: Reason for rejection
        db_path: Optional explicit database path

    Returns:
        True if rejected, False otherwise
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        rows = db.execute_update(
            """
            UPDATE observation_discovered
            SET status = ?, rejected_at = ?, rejection_reason = ?
            WHERE id = ?
            """,
            (
                ObservationStatus.REJECTED.value,
                datetime.now().isoformat(),
                reason,
                observation_id,
            ),
        )

        return rows > 0

    except Exception as e:
        logger.warning(f"Failed to reject observation: {e}")
        return False


def get_observations_by_status(
    status: ObservationStatus,
    observation_type: ObservationType | None = None,
    limit: int = 100,
    db_path: Path | None = None,
) -> list[dict]:
    """Get observations by status.

    Args:
        status: Observation status to filter by
        observation_type: Optional type filter
        limit: Maximum results
        db_path: Optional explicit database path

    Returns:
        List of observation dictionaries
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        if observation_type:
            rows = db.execute(
                """
                SELECT * FROM observation_discovered
                WHERE status = ? AND observation_type = ?
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                (status.value, observation_type.value, limit),
            )
        else:
            rows = db.execute(
                """
                SELECT * FROM observation_discovered
                WHERE status = ?
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            )

        return [dict(row) for row in rows]

    except Exception as e:
        logger.warning(f"Failed to get observations: {e}")
        return []


def get_observation_stats(db_path: Path | None = None) -> dict:
    """Get observation statistics.

    Returns:
        Dictionary with observation counts by status and type
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Count by status
        by_status = db.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM observation_discovered
            GROUP BY status
            """
        )

        # Count by type (non-rejected/archived)
        by_type = db.execute(
            """
            SELECT observation_type, COUNT(*) as cnt
            FROM observation_discovered
            WHERE status NOT IN ('REJECTED', 'ARCHIVED')
            GROUP BY observation_type
            """
        )

        # Count by guidance type
        by_guidance = db.execute(
            """
            SELECT guidance_type, COUNT(*) as cnt
            FROM observation_discovered
            WHERE guidance_type IS NOT NULL
            GROUP BY guidance_type
            """
        )

        # Implemented count
        implemented = db.execute_one(
            "SELECT COUNT(*) as cnt FROM observation_implemented WHERE status = 'ACTIVE'"
        )

        return {
            "by_status": {row["status"]: row["cnt"] for row in by_status},
            "by_type": {row["observation_type"]: row["cnt"] for row in by_type},
            "by_guidance": {row["guidance_type"]: row["cnt"] for row in by_guidance},
            "implemented_count": implemented["cnt"] if implemented else 0,
        }

    except Exception as e:
        logger.warning(f"Failed to get observation stats: {e}")
        return {
            "by_status": {},
            "by_type": {},
            "by_guidance": {},
            "implemented_count": 0,
        }
