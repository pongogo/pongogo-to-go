"""
Artifact discovery and implementation lifecycle.

Manages file-based knowledge discovered from CLAUDE.md, wiki/, docs/ that can be
promoted to instruction files.

Lifecycle: DISCOVERED → REVIEWING → PROMOTED → (optionally) ARCHIVED
"""

import hashlib
import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from .database import PongogoDatabase, get_default_db_path

logger = logging.getLogger(__name__)


class ArtifactStatus(str, Enum):
    """Status in artifact lifecycle."""

    DISCOVERED = "DISCOVERED"  # Found during scan
    REVIEWING = "REVIEWING"  # Under consideration
    PROMOTED = "PROMOTED"  # Became an instruction file
    ARCHIVED = "ARCHIVED"  # No longer relevant


class SourceType(str, Enum):
    """Type of source file."""

    CLAUDE_MD = "CLAUDE_MD"
    WIKI = "WIKI"
    DOCS = "DOCS"
    OTHER = "OTHER"


def store_artifact_discovery(
    source_file: str,
    source_type: SourceType,
    section_content: str,
    section_title: str | None = None,
    keywords: list[str] | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Store a newly discovered artifact.

    Args:
        source_file: Path to source file relative to project root
        source_type: Type of source (CLAUDE_MD, WIKI, DOCS, OTHER)
        section_content: Raw content of the section
        section_title: Optional heading from source file
        keywords: Optional list of extracted keywords
        db_path: Optional explicit database path

    Returns:
        Row ID if new discovery, None if duplicate (same content_hash exists)
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(section_content.encode()).hexdigest()

        # Check for existing
        existing = db.execute_one(
            "SELECT id FROM artifact_discovered WHERE content_hash = ?",
            (content_hash,),
        )
        if existing:
            logger.debug(f"Duplicate artifact, skipping: {source_file}")
            return None

        keywords_json = json.dumps(keywords) if keywords else None

        row_id = db.execute_insert(
            """
            INSERT INTO artifact_discovered
            (source_file, source_type, section_title, section_content,
             content_hash, keywords, status, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_file,
                source_type.value,
                section_title,
                section_content,
                content_hash,
                keywords_json,
                ArtifactStatus.DISCOVERED.value,
                datetime.now().isoformat(),
            ),
        )

        logger.debug(f"Stored artifact discovery: {source_file}/{section_title}")
        return row_id

    except Exception as e:
        logger.warning(f"Failed to store artifact: {e}")
        return None


def promote_artifact(
    discovered_id: int,
    instruction_file: str,
    instruction_id: str | None = None,
    instruction_category: str | None = None,
    title: str | None = None,
    description: str | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Promote a discovered artifact to an implemented instruction.

    Args:
        discovered_id: ID of artifact_discovered record
        instruction_file: Path to created instruction file
        instruction_id: Semantic ID (e.g., "work_logging")
        instruction_category: Category (e.g., "project_management")
        title: Human-readable title
        description: Brief description
        db_path: Optional explicit database path

    Returns:
        Row ID of artifact_implemented record
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Get discovered artifact
        discovered = db.execute_one(
            "SELECT * FROM artifact_discovered WHERE id = ?",
            (discovered_id,),
        )
        if not discovered:
            logger.warning(f"Artifact not found: {discovered_id}")
            return None

        now = datetime.now().isoformat()

        # Create implemented record
        content_hash = hashlib.sha256(
            discovered["section_content"].encode()
        ).hexdigest()
        word_count = len(discovered["section_content"].split())

        impl_id = db.execute_insert(
            """
            INSERT INTO artifact_implemented
            (discovered_id, instruction_file, instruction_id, instruction_category,
             content_hash, word_count, title, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                discovered_id,
                instruction_file,
                instruction_id,
                instruction_category,
                content_hash,
                word_count,
                title or discovered["section_title"],
                description,
                "ACTIVE",
                now,
            ),
        )

        # Update discovered record
        db.execute_update(
            """
            UPDATE artifact_discovered
            SET status = ?, promoted_to = ?, promoted_at = ?
            WHERE id = ?
            """,
            (ArtifactStatus.PROMOTED.value, impl_id, now, discovered_id),
        )

        logger.info(f"Promoted artifact {discovered_id} → {instruction_file}")
        return impl_id

    except Exception as e:
        logger.warning(f"Failed to promote artifact: {e}")
        return None


def get_artifacts_by_status(
    status: ArtifactStatus,
    source_type: SourceType | None = None,
    limit: int = 100,
    db_path: Path | None = None,
) -> list[dict]:
    """Get artifacts by status.

    Args:
        status: Artifact status to filter by
        source_type: Optional source type filter
        limit: Maximum results
        db_path: Optional explicit database path

    Returns:
        List of artifact dictionaries
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        if source_type:
            rows = db.execute(
                """
                SELECT * FROM artifact_discovered
                WHERE status = ? AND source_type = ?
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                (status.value, source_type.value, limit),
            )
        else:
            rows = db.execute(
                """
                SELECT * FROM artifact_discovered
                WHERE status = ?
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            )

        return [dict(row) for row in rows]

    except Exception as e:
        logger.warning(f"Failed to get artifacts: {e}")
        return []


def archive_artifact(
    artifact_id: int,
    reason: str,
    db_path: Path | None = None,
) -> bool:
    """Archive a discovered artifact.

    Args:
        artifact_id: ID of artifact to archive
        reason: Reason for archiving
        db_path: Optional explicit database path

    Returns:
        True if archived, False otherwise
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        rows = db.execute_update(
            """
            UPDATE artifact_discovered
            SET status = ?, archived_at = ?, archive_reason = ?
            WHERE id = ?
            """,
            (ArtifactStatus.ARCHIVED.value, datetime.now().isoformat(), reason, artifact_id),
        )

        return rows > 0

    except Exception as e:
        logger.warning(f"Failed to archive artifact: {e}")
        return False


def get_artifact_stats(db_path: Path | None = None) -> dict:
    """Get artifact statistics.

    Returns:
        Dictionary with artifact counts by status and source type
    """
    try:
        db = PongogoDatabase(db_path=db_path or get_default_db_path())

        # Count by status
        by_status = db.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM artifact_discovered
            GROUP BY status
            """
        )

        # Count by source type (non-archived)
        by_source = db.execute(
            """
            SELECT source_type, COUNT(*) as cnt
            FROM artifact_discovered
            WHERE status != 'ARCHIVED'
            GROUP BY source_type
            """
        )

        # Implemented count
        implemented = db.execute_one(
            "SELECT COUNT(*) as cnt FROM artifact_implemented WHERE status = 'ACTIVE'"
        )

        return {
            "by_status": {row["status"]: row["cnt"] for row in by_status},
            "by_source": {row["source_type"]: row["cnt"] for row in by_source},
            "implemented_count": implemented["cnt"] if implemented else 0,
        }

    except Exception as e:
        logger.warning(f"Failed to get artifact stats: {e}")
        return {"by_status": {}, "by_source": {}, "implemented_count": 0}
