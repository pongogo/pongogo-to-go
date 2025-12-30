"""
PI System Queries - Gardening and analysis queries.
"""

from datetime import datetime, timedelta
from typing import Any

from .database import PIDatabase
from .models import (
    PIClassification,
    PIConfidence,
    PIEvidence,
    PIRelationship,
    PIStatus,
    PotentialImprovement,
    RelationshipType,
)


class PIQueries:
    """Query interface for PI gardening and analysis."""

    def __init__(self, db: PIDatabase):
        self.db = db

    # =========================================================================
    # Basic Queries
    # =========================================================================

    def get_all(self, include_archived: bool = False) -> list[PotentialImprovement]:
        """Get all PIs, optionally including archived."""
        where = "" if include_archived else "WHERE archived = 0"
        rows = self.db.execute(
            f"SELECT * FROM potential_improvements {where} ORDER BY id"
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def get_by_id(self, pi_id: str) -> PotentialImprovement | None:
        """Get a PI by its ID."""
        row = self.db.execute_one(
            "SELECT * FROM potential_improvements WHERE id = ?", (pi_id,)
        )
        return PotentialImprovement.from_row(row) if row else None

    def get_by_status(self, status: PIStatus) -> list[PotentialImprovement]:
        """Get PIs by status."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE status = ? AND archived = 0 ORDER BY id",
            (status.value,),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def get_by_confidence(self, confidence: PIConfidence) -> list[PotentialImprovement]:
        """Get PIs by confidence level."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE confidence = ? AND archived = 0 ORDER BY id",
            (confidence.value,),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def get_by_classification(
        self, classification: PIClassification
    ) -> list[PotentialImprovement]:
        """Get PIs by classification."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE classification = ? AND archived = 0 ORDER BY id",
            (classification.value,),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def get_by_cluster(self, cluster: str) -> list[PotentialImprovement]:
        """Get PIs by cluster."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE cluster = ? AND archived = 0 ORDER BY id",
            (cluster,),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    # =========================================================================
    # Gardening Queries
    # =========================================================================

    def find_stale(self, days: int = 90) -> list[PotentialImprovement]:
        """
        Find PIs with no evidence in the specified number of days.

        A PI is considered stale if:
        - It has no evidence records, OR
        - Its most recent evidence is older than `days` days
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # PIs with no evidence at all
        no_evidence_sql = """
            SELECT p.* FROM potential_improvements p
            LEFT JOIN pi_evidence e ON p.id = e.pi_id
            WHERE p.archived = 0
            GROUP BY p.id
            HAVING COUNT(e.id) = 0
        """

        # PIs with stale evidence
        stale_evidence_sql = """
            SELECT p.* FROM potential_improvements p
            INNER JOIN (
                SELECT pi_id, MAX(date) as last_evidence
                FROM pi_evidence
                GROUP BY pi_id
            ) latest ON p.id = latest.pi_id
            WHERE p.archived = 0 AND latest.last_evidence < ?
        """

        no_evidence = self.db.execute(no_evidence_sql)
        stale_evidence = self.db.execute(stale_evidence_sql, (cutoff_date,))

        # Combine and deduplicate
        all_stale = {row["id"]: row for row in list(no_evidence) + list(stale_evidence)}
        return [PotentialImprovement.from_row(row) for row in all_stale.values()]

    def find_duplicates(self) -> list[PIRelationship]:
        """Find all duplicate relationships."""
        rows = self.db.execute(
            "SELECT * FROM pi_relationships WHERE relationship_type = ?",
            (RelationshipType.DUPLICATE.value,),
        )
        return [PIRelationship.from_row(row) for row in rows]

    def find_ready_for_implementation(self) -> list[PotentialImprovement]:
        """
        Find PIs ready for implementation.

        Criteria:
        - Confidence is MEDIUM or HIGH
        - Status is CANDIDATE or VALIDATED
        - Not archived
        """
        rows = self.db.execute(
            """
            SELECT * FROM potential_improvements
            WHERE confidence IN (?, ?)
            AND status IN (?, ?)
            AND archived = 0
            ORDER BY confidence DESC, occurrence_count DESC
        """,
            (
                PIConfidence.MEDIUM.value,
                PIConfidence.HIGH.value,
                PIStatus.CANDIDATE.value,
                PIStatus.VALIDATED.value,
            ),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def find_unclassified(self) -> list[PotentialImprovement]:
        """Find PIs without classification."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE classification IS NULL AND archived = 0 ORDER BY id"
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    def find_unclustered(self) -> list[PotentialImprovement]:
        """Find PIs without cluster assignment."""
        rows = self.db.execute(
            "SELECT * FROM potential_improvements WHERE cluster IS NULL AND archived = 0 ORDER BY id"
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    # =========================================================================
    # Relationship Queries
    # =========================================================================

    def get_relationships(self, pi_id: str) -> list[PIRelationship]:
        """Get all relationships involving a PI."""
        rows = self.db.execute(
            """
            SELECT * FROM pi_relationships
            WHERE pi_id_1 = ? OR pi_id_2 = ?
            ORDER BY relationship_type
        """,
            (pi_id, pi_id),
        )
        return [PIRelationship.from_row(row) for row in rows]

    def get_related_pis(self, pi_id: str) -> list[PotentialImprovement]:
        """Get all PIs related to the given PI."""
        rows = self.db.execute(
            """
            SELECT p.* FROM potential_improvements p
            INNER JOIN pi_relationships r ON (p.id = r.pi_id_1 OR p.id = r.pi_id_2)
            WHERE (r.pi_id_1 = ? OR r.pi_id_2 = ?) AND p.id != ?
        """,
            (pi_id, pi_id, pi_id),
        )
        return [PotentialImprovement.from_row(row) for row in rows]

    # =========================================================================
    # Evidence Queries
    # =========================================================================

    def get_evidence(self, pi_id: str) -> list[PIEvidence]:
        """Get all evidence for a PI."""
        rows = self.db.execute(
            "SELECT * FROM pi_evidence WHERE pi_id = ? ORDER BY date DESC", (pi_id,)
        )
        return [PIEvidence.from_row(row) for row in rows]

    def get_latest_evidence_date(self, pi_id: str) -> str | None:
        """Get the date of the most recent evidence for a PI."""
        row = self.db.execute_one(
            "SELECT MAX(date) as latest FROM pi_evidence WHERE pi_id = ?", (pi_id,)
        )
        return row["latest"] if row else None

    # =========================================================================
    # Statistics Queries
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get overall PI system statistics."""
        total = self.db.count("potential_improvements", "archived = 0")
        archived = self.db.count("potential_improvements", "archived = 1")

        by_status = {}
        for status in PIStatus:
            count = self.db.count(
                "potential_improvements", "status = ? AND archived = 0", (status.value,)
            )
            if count > 0:
                by_status[status.value] = count

        by_confidence = {}
        for conf in PIConfidence:
            count = self.db.count(
                "potential_improvements",
                "confidence = ? AND archived = 0",
                (conf.value,),
            )
            if count > 0:
                by_confidence[conf.value] = count

        by_classification = {}
        for cls in PIClassification:
            count = self.db.count(
                "potential_improvements",
                "classification = ? AND archived = 0",
                (cls.value,),
            )
            if count > 0:
                by_classification[cls.value] = count
        unclassified = self.db.count(
            "potential_improvements", "classification IS NULL AND archived = 0"
        )
        if unclassified > 0:
            by_classification["UNCLASSIFIED"] = unclassified

        # Cluster distribution
        cluster_rows = self.db.execute("""
            SELECT cluster, COUNT(*) as count
            FROM potential_improvements
            WHERE archived = 0 AND cluster IS NOT NULL
            GROUP BY cluster
            ORDER BY count DESC
        """)
        by_cluster = {row["cluster"]: row["count"] for row in cluster_rows}

        return {
            "total_active": total,
            "total_archived": archived,
            "by_status": by_status,
            "by_confidence": by_confidence,
            "by_classification": by_classification,
            "by_cluster": by_cluster,
            "relationships": self.db.count("pi_relationships"),
            "evidence_records": self.db.count("pi_evidence"),
        }

    def get_clusters(self) -> list[str]:
        """Get list of all clusters."""
        rows = self.db.execute("""
            SELECT DISTINCT cluster FROM potential_improvements
            WHERE cluster IS NOT NULL AND archived = 0
            ORDER BY cluster
        """)
        return [row["cluster"] for row in rows]
