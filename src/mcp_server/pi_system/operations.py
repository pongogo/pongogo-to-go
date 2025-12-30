"""
PI System Operations - CRUD and management operations.
"""

from datetime import datetime
from pathlib import Path

from .database import PIDatabase
from .models import (
    ImplementationType,
    PIClassification,
    PIConfidence,
    PIEvidence,
    PIImplementation,
    PIRelationship,
    PIStatus,
    PotentialImprovement,
    RelationshipType,
)
from .queries import PIQueries


class PISystem:
    """
    Main interface for PI System operations.

    Provides CRUD operations, gardening queries, and file sync capabilities.
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize PI System.

        Args:
            db_path: Path to SQLite database. Defaults to docs/project_management/potential_improvements.db
        """
        self.db = PIDatabase(db_path)
        self.queries = PIQueries(self.db)

    # =========================================================================
    # PI CRUD Operations
    # =========================================================================

    def create_pi(
        self,
        pi_id: str,
        title: str,
        summary: str | None = None,
        status: PIStatus = PIStatus.CANDIDATE,
        confidence: PIConfidence = PIConfidence.LOW,
        classification: PIClassification | None = None,
        cluster: str | None = None,
        source_task: str | None = None,
        file_path: str | None = None,
        identified_date: str | None = None,
    ) -> PotentialImprovement:
        """
        Create a new Potential Improvement.

        Args:
            pi_id: Unique identifier (e.g., "PI-001")
            title: Short descriptive title
            summary: Brief summary of the improvement
            status: Initial status (default: CANDIDATE)
            confidence: Confidence level (default: LOW)
            classification: CORRECTIVE or EXPLORATORY
            cluster: Domain cluster name
            source_task: Task that identified this PI
            file_path: Path to detailed markdown file
            identified_date: Date identified (default: today)

        Returns:
            Created PotentialImprovement
        """
        now = datetime.now().strftime("%Y-%m-%d")
        pi = PotentialImprovement(
            id=pi_id,
            title=title,
            summary=summary,
            status=status,
            confidence=confidence,
            classification=classification,
            cluster=cluster,
            identified_date=identified_date or now,
            last_updated=now,
            source_task=source_task,
            file_path=file_path,
        )

        data = pi.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT INTO potential_improvements ({columns}) VALUES ({placeholders})"

        self.db.execute(sql, tuple(data.values()))
        return pi

    def update_pi(
        self,
        pi_id: str,
        title: str | None = None,
        summary: str | None = None,
        status: PIStatus | None = None,
        confidence: PIConfidence | None = None,
        classification: PIClassification | None = None,
        cluster: str | None = None,
        occurrence_count: int | None = None,
    ) -> PotentialImprovement | None:
        """
        Update an existing PI.

        Args:
            pi_id: PI to update
            **kwargs: Fields to update

        Returns:
            Updated PotentialImprovement or None if not found
        """
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if status is not None:
            updates.append("status = ?")
            params.append(status.value if isinstance(status, PIStatus) else status)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(
                confidence.value if isinstance(confidence, PIConfidence) else confidence
            )
        if classification is not None:
            updates.append("classification = ?")
            params.append(
                classification.value
                if isinstance(classification, PIClassification)
                else classification
            )
        if cluster is not None:
            updates.append("cluster = ?")
            params.append(cluster)
        if occurrence_count is not None:
            updates.append("occurrence_count = ?")
            params.append(occurrence_count)

        if not updates:
            return self.queries.get_by_id(pi_id)

        updates.append("last_updated = ?")
        params.append(datetime.now().strftime("%Y-%m-%d"))
        params.append(pi_id)

        sql = f"UPDATE potential_improvements SET {', '.join(updates)} WHERE id = ?"
        self.db.execute(sql, tuple(params))

        return self.queries.get_by_id(pi_id)

    def archive_pi(self, pi_id: str) -> bool:
        """Archive a PI (soft delete)."""
        self.db.execute(
            "UPDATE potential_improvements SET archived = 1, last_updated = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d"), pi_id),
        )
        return True

    def delete_pi(self, pi_id: str) -> bool:
        """Permanently delete a PI and all related records."""
        self.db.execute("DELETE FROM potential_improvements WHERE id = ?", (pi_id,))
        return True

    # =========================================================================
    # Evidence Operations
    # =========================================================================

    def add_evidence(
        self,
        pi_id: str,
        source: str,
        description: str | None = None,
        date: str | None = None,
    ) -> PIEvidence:
        """
        Add evidence/occurrence to a PI.

        Also increments occurrence_count and may update confidence.

        Args:
            pi_id: PI to add evidence to
            source: Source of evidence (e.g., "", "RCA-2025-11-15")
            description: Description of the occurrence
            date: Date of occurrence (default: today)

        Returns:
            Created PIEvidence
        """
        evidence = PIEvidence(
            pi_id=pi_id,
            date=date or datetime.now().strftime("%Y-%m-%d"),
            source=source,
            description=description,
        )

        data = evidence.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT INTO pi_evidence ({columns}) VALUES ({placeholders})"
        self.db.execute(sql, tuple(data.values()))

        # Update occurrence count and potentially confidence
        pi = self.queries.get_by_id(pi_id)
        if pi:
            new_count = pi.occurrence_count + 1
            new_confidence = self._calculate_confidence(new_count)
            self.update_pi(pi_id, occurrence_count=new_count, confidence=new_confidence)

        return evidence

    def _calculate_confidence(self, occurrence_count: int) -> PIConfidence:
        """Calculate confidence level from occurrence count."""
        if occurrence_count >= 5:
            return PIConfidence.HIGH
        elif occurrence_count >= 3:
            return PIConfidence.MEDIUM
        return PIConfidence.LOW

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    def add_relationship(
        self,
        pi_id_1: str,
        pi_id_2: str,
        relationship_type: RelationshipType,
        notes: str | None = None,
    ) -> PIRelationship:
        """
        Add a relationship between two PIs.

        Args:
            pi_id_1: First PI
            pi_id_2: Second PI
            relationship_type: Type of relationship
            notes: Additional notes

        Returns:
            Created PIRelationship
        """
        relationship = PIRelationship(
            pi_id_1=pi_id_1,
            pi_id_2=pi_id_2,
            relationship_type=relationship_type,
            notes=notes,
            discovered_date=datetime.now().strftime("%Y-%m-%d"),
        )

        data = relationship.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT OR REPLACE INTO pi_relationships ({columns}) VALUES ({placeholders})"
        self.db.execute(sql, tuple(data.values()))

        return relationship

    def remove_relationship(
        self,
        pi_id_1: str,
        pi_id_2: str,
        relationship_type: RelationshipType,
    ) -> bool:
        """Remove a relationship between two PIs."""
        self.db.execute(
            "DELETE FROM pi_relationships WHERE pi_id_1 = ? AND pi_id_2 = ? AND relationship_type = ?",
            (pi_id_1, pi_id_2, relationship_type.value),
        )
        return True

    # =========================================================================
    # Implementation Operations
    # =========================================================================

    def mark_implemented(
        self,
        pi_id: str,
        implementation_type: ImplementationType,
        location: str,
        notes: str | None = None,
    ) -> PIImplementation:
        """
        Mark a PI as implemented.

        Args:
            pi_id: PI to mark
            implementation_type: Type of implementation
            location: Where implemented (file path, wiki page, etc.)
            notes: Additional notes

        Returns:
            Created PIImplementation
        """
        impl = PIImplementation(
            pi_id=pi_id,
            implementation_date=datetime.now().strftime("%Y-%m-%d"),
            implementation_type=implementation_type,
            location=location,
            notes=notes,
        )

        data = impl.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT OR REPLACE INTO pi_implementations ({columns}) VALUES ({placeholders})"
        self.db.execute(sql, tuple(data.values()))

        # Update status
        self.update_pi(pi_id, status=PIStatus.IMPLEMENTED)

        return impl

    # =========================================================================
    # Note: No bulk operations by design
    # =========================================================================
    # Agent-first design principle: Agents should iterate through items
    # individually, making deliberate decisions for each. Bulk operations
    # bypass the careful consideration that foundational data requires.
    # See PI-064 (Active Enforcement Architecture) for rationale.

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_next_pi_id(self) -> str:
        """Get the next available PI ID."""
        row = self.db.execute_one("""
            SELECT id FROM potential_improvements
            ORDER BY CAST(SUBSTR(id, 4) AS INTEGER) DESC
            LIMIT 1
        """)
        if row:
            current_num = int(row["id"].split("-")[1])
            return f"PI-{current_num + 1:03d}"
        return "PI-001"

    def update_status(
        self,
        pi_id: str,
        new_status: PIStatus,
        new_confidence: PIConfidence | None = None,
    ) -> PotentialImprovement | None:
        """Convenience method to update status and optionally confidence."""
        return self.update_pi(pi_id, status=new_status, confidence=new_confidence)

    def classify(
        self,
        pi_id: str,
        classification: PIClassification,
        reason: str,
        model: str = "claude-opus-4-5-20251101",
    ) -> PotentialImprovement | None:
        """
        Classify a PI with reasoning.

        This is the primary method for classification - captures the reasoning
        and model information for auditability and future multi-model comparison.

        Args:
            pi_id: PI to classify
            classification: CORRECTIVE or EXPLORATORY
            reason: Why this classification was chosen (required for auditability)
            model: Which model made the classification

        Returns:
            Updated PotentialImprovement
        """
        now = datetime.now().strftime("%Y-%m-%d")
        classification_value = (
            classification.value
            if isinstance(classification, PIClassification)
            else classification
        )

        self.db.execute(
            """
            UPDATE potential_improvements
            SET classification = ?,
                classification_reason = ?,
                classification_model = ?,
                classification_date = ?,
                last_updated = ?
            WHERE id = ?
        """,
            (classification_value, reason, model, now, now, pi_id),
        )

        return self.queries.get_by_id(pi_id)

    def update_classification(
        self,
        pi_id: str,
        classification: PIClassification,
    ) -> PotentialImprovement | None:
        """
        DEPRECATED: Use classify() instead which captures reasoning.

        This method exists for backwards compatibility but should not be used
        for new classifications.
        """
        return self.update_pi(pi_id, classification=classification)

    # =========================================================================
    # Query Delegation
    # =========================================================================

    def get_all(self, include_archived: bool = False) -> list[PotentialImprovement]:
        """Get all PIs."""
        return self.queries.get_all(include_archived)

    def get_by_id(self, pi_id: str) -> PotentialImprovement | None:
        """Get a PI by ID."""
        return self.queries.get_by_id(pi_id)

    def find_stale(self, days: int = 90) -> list[PotentialImprovement]:
        """Find stale PIs."""
        return self.queries.find_stale(days)

    def find_duplicates(self) -> list[PIRelationship]:
        """Find duplicate relationships."""
        return self.queries.find_duplicates()

    def find_ready_for_implementation(self) -> list[PotentialImprovement]:
        """Find PIs ready for implementation."""
        return self.queries.find_ready_for_implementation()

    def find_unclassified(self) -> list[PotentialImprovement]:
        """Find unclassified PIs."""
        return self.queries.find_unclassified()

    def get_stats(self) -> dict:
        """Get statistics."""
        return self.queries.get_stats()

    def get_clusters(self) -> list[str]:
        """Get all clusters."""
        return self.queries.get_clusters()

    def get_relationships(self, pi_id: str) -> list[PIRelationship]:
        """Get relationships for a PI."""
        return self.queries.get_relationships(pi_id)

    def get_evidence(self, pi_id: str) -> list[PIEvidence]:
        """Get evidence for a PI."""
        return self.queries.get_evidence(pi_id)
