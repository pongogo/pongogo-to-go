"""
Discovery System Operations - Main System Interface

Provides high-level operations for discovery scanning, matching, and promotion.

Refactored to use unified database (schema v3.0.0) at .pongogo/pongogo.db
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..database.database import PongogoDatabase, get_default_db_path
from .scanner import DiscoveryScanner


@dataclass
class Discovery:
    """A discovery record from the database (artifact_discovered table)."""

    id: int
    source_file: str
    source_type: str
    section_title: str | None
    section_content: str
    content_hash: str
    keywords: list[str]
    status: str
    promoted_to: int | None  # FK to artifact_implemented.id
    discovered_at: str
    promoted_at: str | None
    archived_at: str | None
    archive_reason: str | None

    @classmethod
    def from_row(cls, row) -> "Discovery":
        """Create Discovery from database row."""
        return cls(
            id=row["id"],
            source_file=row["source_file"],
            source_type=row["source_type"],
            section_title=row["section_title"],
            section_content=row["section_content"],
            content_hash=row["content_hash"],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            status=row["status"],
            promoted_to=row["promoted_to"],
            discovered_at=row["discovered_at"],
            promoted_at=row["promoted_at"],
            archived_at=row["archived_at"],
            archive_reason=row["archive_reason"],
        )


@dataclass
class ScanResult:
    """Result of a discovery scan operation."""

    total_discoveries: int
    new_discoveries: int
    updated_discoveries: int
    by_source: dict  # source_type -> {files: int, sections: int}


class DiscoverySystem:
    """
    Main interface for the Discovery System.

    Coordinates scanning, storage, matching, and promotion of discoveries.
    Uses unified database at .pongogo/pongogo.db (schema v3.0.0).
    """

    def __init__(self, project_root: Path):
        """
        Initialize Discovery System for a project.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root)
        self.db = PongogoDatabase(project_root=project_root)
        self.scanner = DiscoveryScanner(project_root)

    def scan_repository(self) -> ScanResult:
        """
        Scan repository for knowledge patterns and store in database.

        Returns:
            ScanResult with counts of discoveries found
        """
        discoveries = self.scanner.scan_all()
        summary = self.scanner.get_scan_summary(discoveries)

        new_count = 0
        updated_count = 0
        now = datetime.utcnow().isoformat()

        for d in discoveries:
            # Check if we already have this content (by hash)
            existing = self.db.execute_one(
                "SELECT id FROM artifact_discovered WHERE content_hash = ?",
                (d.content_hash,),
            )

            if existing:
                # Content unchanged, nothing to do
                updated_count += 1
            else:
                # Check if same source_file + section_title exists (updated content)
                existing_by_location = self.db.execute_one(
                    """
                    SELECT id FROM artifact_discovered
                    WHERE source_file = ? AND section_title = ?
                    """,
                    (d.source_file, d.section_title),
                )

                if existing_by_location:
                    # Update existing discovery with new content
                    self.db.execute_update(
                        """
                        UPDATE artifact_discovered
                        SET section_content = ?, content_hash = ?, keywords = ?,
                            discovered_at = ?
                        WHERE id = ?
                        """,
                        (
                            d.section_content,
                            d.content_hash,
                            json.dumps(d.keywords),
                            now,
                            existing_by_location["id"],
                        ),
                    )
                    updated_count += 1
                else:
                    # Insert new discovery
                    self.db.execute_insert(
                        """
                        INSERT INTO artifact_discovered
                        (source_file, source_type, section_title, section_content,
                         content_hash, keywords, status, discovered_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'DISCOVERED', ?)
                        """,
                        (
                            d.source_file,
                            d.source_type,
                            d.section_title,
                            d.section_content,
                            d.content_hash,
                            json.dumps(d.keywords),
                            now,
                        ),
                    )
                    new_count += 1

        # Record scan in history
        for source_type, data in summary.get("by_source", {}).items():
            self.db.execute_insert(
                """
                INSERT INTO scan_history
                (scan_date, scan_type, source_type, files_scanned, sections_found,
                 new_discoveries, updated_discoveries)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    "repository_scan",
                    source_type,
                    data.get("files", 0),
                    data.get("sections", 0),
                    new_count,
                    updated_count,
                ),
            )

        return ScanResult(
            total_discoveries=len(discoveries),
            new_discoveries=new_count,
            updated_discoveries=updated_count,
            by_source=summary.get("by_source", {}),
        )

    def find_matches(self, keywords: list[str], limit: int = 10) -> list[Discovery]:
        """
        Find discoveries matching given keywords.

        Used during routing to check if query matches any discoveries.

        Args:
            keywords: List of keywords to match against
            limit: Maximum number of matches to return

        Returns:
            List of matching Discovery objects, sorted by match score
        """
        if not keywords:
            return []

        # Build SQL for keyword matching
        # Simple approach: count how many keywords match
        discoveries = self.db.execute(
            """
            SELECT * FROM artifact_discovered
            WHERE status = 'DISCOVERED'
            ORDER BY discovered_at DESC
            """
        )

        # Score each discovery by keyword overlap
        scored = []
        keyword_set = {k.lower() for k in keywords}

        for row in discoveries:
            discovery_keywords = set(
                json.loads(row["keywords"]) if row["keywords"] else []
            )
            overlap = len(keyword_set & discovery_keywords)
            if overlap > 0:
                scored.append((overlap, Discovery.from_row(row)))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:limit]]

    def promote(self, discovery_id: int) -> str | None:
        """
        Promote a discovery to an instruction file.

        Creates instruction file in .pongogo/instructions/_discovered/
        and updates discovery status to PROMOTED.

        Args:
            discovery_id: ID of discovery to promote

        Returns:
            Path to created instruction file, or None if failed
        """
        # Get discovery
        row = self.db.execute_one(
            "SELECT * FROM artifact_discovered WHERE id = ?",
            (discovery_id,),
        )
        if not row:
            return None

        discovery = Discovery.from_row(row)

        # Generate instruction file name
        source_prefix = discovery.source_type.lower()
        if discovery.section_title:
            # Sanitize title for filename
            slug = self._slugify(discovery.section_title)
        else:
            # Use source file name
            slug = self._slugify(Path(discovery.source_file).stem)

        filename = f"{source_prefix}_{slug}.instructions.md"
        instruction_dir = (
            self.project_root / ".pongogo" / "instructions" / "_discovered"
        )
        instruction_dir.mkdir(parents=True, exist_ok=True)
        instruction_path = instruction_dir / filename

        # Generate instruction file content
        content = self._generate_instruction_content(discovery)
        instruction_path.write_text(content, encoding="utf-8")

        # Create artifact_implemented record
        now = datetime.utcnow().isoformat()
        relative_path = str(instruction_path.relative_to(self.project_root))
        word_count = len(discovery.section_content.split())

        impl_id = self.db.execute_insert(
            """
            INSERT INTO artifact_implemented
            (discovered_id, instruction_file, instruction_id, instruction_category,
             content_hash, word_count, title, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (
                discovery_id,
                relative_path,
                f"discovered:{slug}",
                self._get_category_from_source(discovery.source_type),
                discovery.content_hash,
                word_count,
                discovery.section_title or "Discovered Knowledge",
                f"Auto-discovered from {discovery.source_file}",
                now,
            ),
        )

        # Update discovery status with link to implemented record
        self.db.execute_update(
            """
            UPDATE artifact_discovered
            SET status = 'PROMOTED', promoted_to = ?, promoted_at = ?
            WHERE id = ?
            """,
            (impl_id, now, discovery_id),
        )

        return relative_path

    def _get_category_from_source(self, source_type: str) -> str:
        """Map source type to instruction category."""
        category_map = {
            "CLAUDE_MD": "project_guidance",
            "WIKI": "architecture",
            "DOCS": "documentation",
        }
        return category_map.get(source_type, "discovered")

    def _generate_instruction_content(self, discovery: Discovery) -> str:
        """Generate instruction file content from a discovery."""
        title = discovery.section_title or "Discovered Knowledge"
        keywords_str = ", ".join(discovery.keywords[:10])

        # Determine category from source type
        category_map = {
            "CLAUDE_MD": "project_guidance",
            "WIKI": "architecture",
            "DOCS": "documentation",
        }
        category = category_map.get(discovery.source_type, "discovered")

        content = f"""---
id: discovered:{self._slugify(title)}
title: {title}
category: {category}
keywords: [{keywords_str}]
source_file: {discovery.source_file}
source_type: {discovery.source_type}
discovered_at: {discovery.discovered_at}
promoted_at: {datetime.utcnow().isoformat()}
auto_generated: true
---

# {title}

> **Source**: Automatically discovered from `{discovery.source_file}` during repository knowledge scan.

{discovery.section_content}
"""
        return content

    def _slugify(self, text: str) -> str:
        """Convert text to a valid filename slug."""
        import re

        # Convert to lowercase and replace spaces/special chars with underscores
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "_", slug)
        slug = slug.strip("_")
        return slug[:50]  # Limit length

    def list_discoveries(
        self,
        status: str | None = None,
        source_type: str | None = None,
        limit: int = 100,
    ) -> list[Discovery]:
        """
        List discoveries with optional filters.

        Args:
            status: Filter by status (DISCOVERED, PROMOTED, ARCHIVED)
            source_type: Filter by source type (CLAUDE_MD, WIKI, DOCS)
            limit: Maximum number to return

        Returns:
            List of Discovery objects
        """
        conditions = []
        params: list = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = self.db.execute(
            f"""
            SELECT * FROM artifact_discovered
            WHERE {where_clause}
            ORDER BY discovered_at DESC
            LIMIT ?
            """,
            tuple(params),
        )

        return [Discovery.from_row(row) for row in rows]

    def get_discovery(self, discovery_id: int) -> Discovery | None:
        """Get a single discovery by ID."""
        row = self.db.execute_one(
            "SELECT * FROM artifact_discovered WHERE id = ?",
            (discovery_id,),
        )
        return Discovery.from_row(row) if row else None

    def archive_discovery(
        self, discovery_id: int, reason: str = "Marked as not useful"
    ) -> bool:
        """
        Archive a discovery (mark as not useful).

        Args:
            discovery_id: ID of discovery to archive
            reason: Reason for archiving

        Returns:
            True if archived, False if not found
        """
        now = datetime.utcnow().isoformat()
        affected = self.db.execute_update(
            """
            UPDATE artifact_discovered
            SET status = 'ARCHIVED', archived_at = ?, archive_reason = ?
            WHERE id = ?
            """,
            (now, reason, discovery_id),
        )
        return affected > 0

    def get_stats(self) -> dict:
        """
        Get discovery system statistics.

        Returns:
            Dictionary with counts and status breakdown
        """
        # Count total
        total_row = self.db.execute_one(
            "SELECT COUNT(*) as cnt FROM artifact_discovered"
        )
        total = total_row["cnt"] if total_row else 0

        # Count by status
        by_status = {}
        for status in ["DISCOVERED", "PROMOTED", "ARCHIVED"]:
            row = self.db.execute_one(
                "SELECT COUNT(*) as cnt FROM artifact_discovered WHERE status = ?",
                (status,),
            )
            by_status[status] = row["cnt"] if row else 0

        # Count by source type (non-archived)
        source_rows = self.db.execute(
            """
            SELECT source_type, COUNT(*) as cnt
            FROM artifact_discovered
            WHERE status != 'ARCHIVED'
            GROUP BY source_type
            """
        )
        by_source = {row["source_type"]: row["cnt"] for row in source_rows}

        return {
            "total": total,
            "by_status": by_status,
            "by_source": by_source,
        }

    def format_scan_summary(self, result: ScanResult) -> str:
        """
        Format scan result for user display.

        Returns:
            Formatted string for terminal output
        """
        lines = ["📚 Repository Knowledge Discovery"]

        if not result.by_source:
            lines.append("   No knowledge sources found")
            return "\n".join(lines)

        for source_type, data in result.by_source.items():
            source_label = {
                "CLAUDE_MD": "CLAUDE.md",
                "WIKI": "wiki/",
                "DOCS": "docs/",
            }.get(source_type, source_type)

            files = data.get("files", 0)
            sections = data.get("sections", 0)

            if source_type == "CLAUDE_MD":
                lines.append(f"   Found {source_label}: {sections} sections cataloged")
            else:
                lines.append(
                    f"   Found {source_label}: {files} files, {sections} sections cataloged"
                )

        lines.append(
            f"   Total: {result.total_discoveries} knowledge patterns discovered"
        )

        if result.new_discoveries > 0:
            lines.append(f"   New discoveries: {result.new_discoveries}")

        return "\n".join(lines)
