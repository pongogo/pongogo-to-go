"""
PI System Sync - File ↔ Database synchronization.

Parses markdown PI files to extract metadata and populates database.
Generates index markdown from database.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    PIClassification,
    PIConfidence,
    PIStatus,
)
from .operations import PISystem

# Default PI files location
DEFAULT_PI_DIR = (
    Path(__file__).parent.parent.parent
    / "docs"
    / "project_management"
    / "potential_improvements"
)
DEFAULT_INDEX_PATH = (
    Path(__file__).parent.parent.parent
    / "docs"
    / "project_management"
    / "potential_improvements.md"
)


class PISync:
    """Synchronize PI markdown files with database."""

    # Regex patterns for extracting metadata from markdown
    PATTERNS = {
        "id": re.compile(r"\*\*ID\*\*:\s*`?(PI-\d+)`?", re.IGNORECASE),
        "title": re.compile(r"^#\s+(?:PI-\d+:?\s*)?(.+)$", re.MULTILINE),
        "status": re.compile(r"\*\*Status\*\*:\s*(\w+)", re.IGNORECASE),
        "confidence": re.compile(r"\*\*Confidence\*\*:\s*(\w+)", re.IGNORECASE),
        "identified": re.compile(
            r"\*\*(?:Identified|Date Identified|Created)\*\*:\s*(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE,
        ),
        "updated": re.compile(
            r"\*\*(?:Last Updated|Updated)\*\*:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
        ),
        "summary_section": re.compile(
            r"##\s*Summary\s*\n+(.*?)(?=\n##|\Z)", re.DOTALL | re.IGNORECASE
        ),
    }

    STATUS_MAP = {
        "candidate": PIStatus.CANDIDATE,
        "tracking": PIStatus.TRACKING,
        "validated": PIStatus.VALIDATED,
        "implemented": PIStatus.IMPLEMENTED,
        "archived": PIStatus.ARCHIVED,
        "deferred": PIStatus.DEFERRED,
        "active": PIStatus.TRACKING,
        "active validation": PIStatus.TRACKING,
        "ready for implementation": PIStatus.VALIDATED,
        "pongogo core requirement": PIStatus.VALIDATED,
    }

    CONFIDENCE_MAP = {
        "low": PIConfidence.LOW,
        "medium": PIConfidence.MEDIUM,
        "high": PIConfidence.HIGH,
    }

    def __init__(
        self,
        pi_system: PISystem | None = None,
        pi_dir: Path | None = None,
        index_path: Path | None = None,
    ):
        """
        Initialize sync.

        Args:
            pi_system: PISystem instance (creates new if None)
            pi_dir: Directory containing PI markdown files
            index_path: Path to generate index markdown
        """
        self.pi_system = pi_system or PISystem()
        self.pi_dir = pi_dir or DEFAULT_PI_DIR
        self.index_path = index_path or DEFAULT_INDEX_PATH

    def sync_from_files(self, reset_db: bool = False) -> dict[str, Any]:
        """
        Parse all PI markdown files and populate database.

        Args:
            reset_db: If True, clear database before syncing

        Returns:
            Dict with sync statistics
        """
        if reset_db:
            self.pi_system.db.reset()

        stats = {
            "files_found": 0,
            "files_parsed": 0,
            "files_failed": [],
            "pis_created": 0,
            "pis_updated": 0,
        }

        # Find all PI files
        pi_files = sorted(self.pi_dir.glob("PI-*.md"))
        stats["files_found"] = len(pi_files)

        for pi_file in pi_files:
            try:
                metadata = self._parse_pi_file(pi_file)
                if metadata:
                    self._upsert_pi(metadata, pi_file)
                    stats["files_parsed"] += 1

                    # Check if created or updated
                    existing = self.pi_system.get_by_id(metadata["id"])
                    if existing:
                        stats["pis_updated"] += 1
                    else:
                        stats["pis_created"] += 1
            except Exception as e:
                stats["files_failed"].append({"file": str(pi_file), "error": str(e)})

        return stats

    def _parse_pi_file(self, file_path: Path) -> dict[str, Any] | None:
        """
        Parse a PI markdown file to extract metadata.

        Args:
            file_path: Path to PI markdown file

        Returns:
            Dict of extracted metadata or None if parsing fails
        """
        content = file_path.read_text(encoding="utf-8")

        # Extract PI ID from filename or content
        pi_id = None
        filename_match = re.match(r"(PI-\d+)", file_path.stem)
        if filename_match:
            pi_id = filename_match.group(1)

        content_match = self.PATTERNS["id"].search(content)
        if content_match:
            pi_id = content_match.group(1)

        if not pi_id:
            return None

        # Extract title
        title_match = self.PATTERNS["title"].search(content)
        title = title_match.group(1).strip() if title_match else file_path.stem

        # Clean up title - remove "Potential Improvement:" prefix if present
        title = re.sub(
            r"^(?:Potential Improvement:?\s*)", "", title, flags=re.IGNORECASE
        ).strip()
        # Remove PI ID from title if duplicated
        title = re.sub(rf"^{re.escape(pi_id)}:?\s*", "", title).strip()

        # Extract status
        status = PIStatus.CANDIDATE
        status_match = self.PATTERNS["status"].search(content)
        if status_match:
            status_text = status_match.group(1).lower().strip()
            # Handle compound statuses like "VALIDATED → Extracted to Pattern Library"
            status_text = status_text.split("→")[0].strip()
            status_text = status_text.split("-")[0].strip()
            status = self.STATUS_MAP.get(status_text, PIStatus.CANDIDATE)

        # Extract confidence
        confidence = PIConfidence.LOW
        confidence_match = self.PATTERNS["confidence"].search(content)
        if confidence_match:
            conf_text = confidence_match.group(1).lower().strip()
            confidence = self.CONFIDENCE_MAP.get(conf_text, PIConfidence.LOW)

        # Also check for confidence in format "MEDIUM (2/3)"
        conf_pattern = re.search(
            r"\*\*Confidence\*\*:\s*(LOW|MEDIUM|HIGH)", content, re.IGNORECASE
        )
        if conf_pattern:
            confidence = self.CONFIDENCE_MAP.get(
                conf_pattern.group(1).lower(), PIConfidence.LOW
            )

        # Extract dates
        identified_match = self.PATTERNS["identified"].search(content)
        identified_date = identified_match.group(1) if identified_match else None

        updated_match = self.PATTERNS["updated"].search(content)
        updated_date = updated_match.group(1) if updated_match else identified_date

        # Extract summary
        summary = None
        summary_match = self.PATTERNS["summary_section"].search(content)
        if summary_match:
            summary = summary_match.group(1).strip()
            # Truncate if too long
            if len(summary) > 500:
                summary = summary[:497] + "..."

        # Extract occurrence count if present
        occurrence_count = 1
        occ_match = re.search(
            r"\((\d+)/\d+(?:\s*occurrences?)?\)", content, re.IGNORECASE
        )
        if occ_match:
            occurrence_count = int(occ_match.group(1))

        # Extract source task if present
        source_task = None
        source_match = re.search(r"(?:Task|Issue|Spike)\s*#?(\d+)", content)
        if source_match:
            source_task = f"#{source_match.group(1)}"

        return {
            "id": pi_id,
            "title": title,
            "summary": summary,
            "status": status,
            "confidence": confidence,
            "identified_date": identified_date,
            "last_updated": updated_date,
            "occurrence_count": occurrence_count,
            "source_task": source_task,
            "file_path": str(file_path.relative_to(file_path.parent.parent.parent)),
        }

    def _upsert_pi(self, metadata: dict[str, Any], file_path: Path):
        """Insert or update a PI in the database."""
        existing = self.pi_system.get_by_id(metadata["id"])

        if existing:
            # Update existing
            self.pi_system.update_pi(
                metadata["id"],
                title=metadata.get("title"),
                summary=metadata.get("summary"),
                status=metadata.get("status"),
                confidence=metadata.get("confidence"),
                occurrence_count=metadata.get("occurrence_count"),
            )
        else:
            # Create new
            self.pi_system.create_pi(
                pi_id=metadata["id"],
                title=metadata["title"],
                summary=metadata.get("summary"),
                status=metadata.get("status", PIStatus.CANDIDATE),
                confidence=metadata.get("confidence", PIConfidence.LOW),
                source_task=metadata.get("source_task"),
                file_path=metadata.get("file_path"),
                identified_date=metadata.get("identified_date"),
            )

    def generate_index(self, output_path: Path | None = None) -> str:
        """
        Generate index markdown from database.

        Args:
            output_path: Where to write index (default: potential_improvements.md)

        Returns:
            Generated markdown content
        """
        output_path = output_path or self.index_path
        stats = self.pi_system.get_stats()
        all_pis = self.pi_system.get_all()

        # Group by confidence
        by_confidence: dict[str, list] = {
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
        }
        for pi in all_pis:
            conf = (
                pi.confidence.value
                if isinstance(pi.confidence, PIConfidence)
                else pi.confidence
            )
            if conf in by_confidence:
                by_confidence[conf].append(pi)

        # Generate markdown
        lines = [
            "# Potential Improvements Tracking",
            "",
            "**Purpose**: Track improvement candidates across learning loops until they reach confidence threshold for implementation",
            "",
            f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d')} (auto-generated from database)",
            "**Status**: Operational",
            "",
            "> **Note**: This file is auto-generated from `potential_improvements.db`. Do not edit directly.",
            "",
            "---",
            "",
            "## Statistics",
            "",
            f"- **Total Active**: {stats['total_active']}",
            f"- **Archived**: {stats['total_archived']}",
            f"- **Relationships**: {stats['relationships']}",
            f"- **Evidence Records**: {stats['evidence_records']}",
            "",
            "### By Confidence",
            "",
        ]

        for conf, count in stats.get("by_confidence", {}).items():
            lines.append(f"- **{conf}**: {count}")

        lines.extend(
            [
                "",
                "### By Status",
                "",
            ]
        )

        for status, count in stats.get("by_status", {}).items():
            lines.append(f"- **{status}**: {count}")

        lines.extend(
            [
                "",
                "---",
                "",
                "## Quick Reference",
                "",
            ]
        )

        # HIGH confidence section
        if by_confidence["HIGH"]:
            lines.extend(
                [
                    "### HIGH Confidence (Ready for Implementation)",
                    "",
                ]
            )
            for pi in by_confidence["HIGH"]:
                status = (
                    pi.status.value if isinstance(pi.status, PIStatus) else pi.status
                )
                lines.append(
                    f"- [{pi.id}](./potential_improvements/{pi.id.replace('-', '_').lower()}.md): {pi.title} ({status})"
                )
            lines.append("")

        # MEDIUM confidence section
        if by_confidence["MEDIUM"]:
            lines.extend(
                [
                    "### MEDIUM Confidence (Validation in Progress)",
                    "",
                ]
            )
            for pi in by_confidence["MEDIUM"]:
                status = (
                    pi.status.value if isinstance(pi.status, PIStatus) else pi.status
                )
                lines.append(
                    f"- [{pi.id}](./potential_improvements/{pi.id.replace('-', '_').lower()}.md): {pi.title} ({status})"
                )
            lines.append("")

        # LOW confidence section
        if by_confidence["LOW"]:
            lines.extend(
                [
                    "### LOW Confidence (Monitoring)",
                    "",
                ]
            )
            for pi in by_confidence["LOW"]:
                status = (
                    pi.status.value if isinstance(pi.status, PIStatus) else pi.status
                )
                lines.append(
                    f"- [{pi.id}](./potential_improvements/{pi.id.replace('-', '_').lower()}.md): {pi.title} ({status})"
                )
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## All Potential Improvements",
                "",
            ]
        )

        # Full list sorted by ID
        for pi in sorted(all_pis, key=lambda p: int(p.id.split("-")[1])):
            conf = (
                pi.confidence.value
                if isinstance(pi.confidence, PIConfidence)
                else pi.confidence
            )
            status = pi.status.value if isinstance(pi.status, PIStatus) else pi.status
            classification = ""
            if pi.classification:
                cls = (
                    pi.classification.value
                    if isinstance(pi.classification, PIClassification)
                    else pi.classification
                )
                classification = f" | {cls}"

            lines.append(f"### {pi.id}: {pi.title}")
            lines.append(
                f"**Confidence**: {conf} | **Status**: {status}{classification}"
            )
            if pi.summary:
                lines.append("")
                lines.append(
                    pi.summary[:200] + ("..." if len(pi.summary) > 200 else "")
                )
            lines.append("")
            lines.append(
                f"[View Full Details](./potential_improvements/{Path(pi.file_path).name if pi.file_path else pi.id.lower().replace('-', '_') + '.md'})"
            )
            lines.append("")
            lines.append("---")
            lines.append("")

        content = "\n".join(lines)

        # Write to file
        output_path.write_text(content, encoding="utf-8")

        return content

    def validate_consistency(self) -> dict[str, Any]:
        """
        Validate consistency between files and database.

        Returns:
            Dict with validation results
        """
        results = {
            "files_without_db": [],
            "db_without_files": [],
            "mismatches": [],
            "valid": True,
        }

        # Get all files
        pi_files = {f.stem: f for f in self.pi_dir.glob("PI-*.md")}
        file_ids = set()
        for stem in pi_files:
            match = re.match(r"(PI-\d+)", stem)
            if match:
                file_ids.add(match.group(1))

        # Get all DB records
        db_pis = {pi.id: pi for pi in self.pi_system.get_all(include_archived=True)}
        db_ids = set(db_pis.keys())

        # Find files without DB records
        results["files_without_db"] = list(file_ids - db_ids)

        # Find DB records without files
        results["db_without_files"] = list(db_ids - file_ids)

        if results["files_without_db"] or results["db_without_files"]:
            results["valid"] = False

        return results
