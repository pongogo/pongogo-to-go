"""
PI System Models - Data classes for PI entities.
"""

from dataclasses import dataclass
from enum import Enum


class PIStatus(str, Enum):
    """Status of a Potential Improvement."""

    CANDIDATE = "CANDIDATE"  # Initial tracking
    TRACKING = "TRACKING"  # Active monitoring for evidence
    VALIDATED = "VALIDATED"  # Confidence threshold reached
    IMPLEMENTED = "IMPLEMENTED"  # Prevention/solution implemented
    ARCHIVED = "ARCHIVED"  # No longer relevant
    DEFERRED = "DEFERRED"  # Intentionally postponed


class PIConfidence(str, Enum):
    """Confidence level based on occurrence count."""

    LOW = "LOW"  # 1-2 occurrences
    MEDIUM = "MEDIUM"  # 3-4 occurrences
    HIGH = "HIGH"  # 5+ occurrences or critical severity


class PIClassification(str, Enum):
    """Classification of PI type."""

    CORRECTIVE = "CORRECTIVE"  # Addresses specific failure mode
    EXPLORATORY = "EXPLORATORY"  # Proposes improvement without failure evidence


class PIType(str, Enum):
    """Type of Potential Improvement / Candidate.

    All types follow the same threshold-based pattern detection:
    - 1st occurrence: Track it
    - 2nd occurrence: Increment, watch for more
    - 3rd+ occurrence: Suggest action
    """

    IMPROVEMENT = "improvement"  # Default - general improvement pattern
    GLOSSARY_CANDIDATE = "glossary_candidate"  # Term needing definition
    FAQ_CANDIDATE = "faq_candidate"  # Question asked repeatedly
    USER_GUIDANCE = "user_guidance"  # User guidance/rule


class RelationshipType(str, Enum):
    """Types of relationships between PIs."""

    OVERLAPS = "OVERLAPS"  # Partial scope intersection
    SUPERSEDES = "SUPERSEDES"  # Newer PI replaces older
    BLOCKS = "BLOCKS"  # One PI blocks another
    RELATED = "RELATED"  # General relationship
    DUPLICATE = "DUPLICATE"  # Same or nearly same content


class ImplementationType(str, Enum):
    """Where a PI was implemented."""

    PATTERN_LIBRARY = "PATTERN_LIBRARY"
    INSTRUCTION_FILE = "INSTRUCTION_FILE"
    PROCESS_DOC = "PROCESS_DOC"
    CODE = "CODE"
    TEMPLATE = "TEMPLATE"
    WIKI = "WIKI"


@dataclass
class PotentialImprovement:
    """Core Potential Improvement entity."""

    id: str  # PI-001, PI-002, etc.
    title: str
    summary: str | None = None
    status: PIStatus = PIStatus.CANDIDATE
    confidence: PIConfidence = PIConfidence.LOW
    classification: PIClassification | None = None
    pi_type: PIType = PIType.IMPROVEMENT
    context: str | None = None  # Additional context (e.g., guidance_type for USER_GUIDANCE)
    classification_reason: str | None = None  # Why this classification
    classification_model: str | None = None  # Which model classified
    classification_date: str | None = None  # When classified
    cluster: str | None = None
    identified_date: str | None = None
    last_updated: str | None = None
    occurrence_count: int = 1
    source_task: str | None = None
    file_path: str | None = None
    archived: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "status": self.status.value
            if isinstance(self.status, PIStatus)
            else self.status,
            "confidence": self.confidence.value
            if isinstance(self.confidence, PIConfidence)
            else self.confidence,
            "classification": self.classification.value
            if isinstance(self.classification, PIClassification)
            else self.classification,
            "pi_type": self.pi_type.value
            if isinstance(self.pi_type, PIType)
            else self.pi_type,
            "context": self.context,
            "classification_reason": self.classification_reason,
            "classification_model": self.classification_model,
            "classification_date": self.classification_date,
            "cluster": self.cluster,
            "identified_date": self.identified_date,
            "last_updated": self.last_updated,
            "occurrence_count": self.occurrence_count,
            "source_task": self.source_task,
            "file_path": self.file_path,
            "archived": 1 if self.archived else 0,
        }

    @classmethod
    def from_row(cls, row) -> "PotentialImprovement":
        """Create from database row."""
        return cls(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            status=PIStatus(row["status"]) if row["status"] else PIStatus.CANDIDATE,
            confidence=PIConfidence(row["confidence"])
            if row["confidence"]
            else PIConfidence.LOW,
            classification=PIClassification(row["classification"])
            if row["classification"]
            else None,
            pi_type=PIType(row["pi_type"])
            if row.get("pi_type")
            else PIType.IMPROVEMENT,
            context=row.get("context"),
            classification_reason=row.get("classification_reason", None),
            classification_model=row.get("classification_model", None),
            classification_date=row.get("classification_date", None),
            cluster=row["cluster"],
            identified_date=row["identified_date"],
            last_updated=row["last_updated"],
            occurrence_count=row["occurrence_count"] or 1,
            source_task=row["source_task"],
            file_path=row["file_path"],
            archived=bool(row["archived"]),
        )


@dataclass
class PIEvidence:
    """Evidence/occurrence record for a PI."""

    pi_id: str
    date: str
    source: str  # , RCA-2025-11-15, etc.
    description: str | None = None
    id: int | None = None  # Database ID (auto-generated)

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "pi_id": self.pi_id,
            "date": self.date,
            "source": self.source,
            "description": self.description,
        }

    @classmethod
    def from_row(cls, row) -> "PIEvidence":
        """Create from database row."""
        return cls(
            id=row["id"],
            pi_id=row["pi_id"],
            date=row["date"],
            source=row["source"],
            description=row["description"],
        )


@dataclass
class PIRelationship:
    """Relationship between two PIs."""

    pi_id_1: str
    pi_id_2: str
    relationship_type: RelationshipType
    notes: str | None = None
    discovered_date: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "pi_id_1": self.pi_id_1,
            "pi_id_2": self.pi_id_2,
            "relationship_type": self.relationship_type.value
            if isinstance(self.relationship_type, RelationshipType)
            else self.relationship_type,
            "notes": self.notes,
            "discovered_date": self.discovered_date,
        }

    @classmethod
    def from_row(cls, row) -> "PIRelationship":
        """Create from database row."""
        return cls(
            pi_id_1=row["pi_id_1"],
            pi_id_2=row["pi_id_2"],
            relationship_type=RelationshipType(row["relationship_type"]),
            notes=row["notes"],
            discovered_date=row["discovered_date"],
        )


@dataclass
class PIImplementation:
    """Implementation record for a PI."""

    pi_id: str
    implementation_date: str | None = None
    implementation_type: ImplementationType | None = None
    location: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "pi_id": self.pi_id,
            "implementation_date": self.implementation_date,
            "implementation_type": self.implementation_type.value
            if isinstance(self.implementation_type, ImplementationType)
            else self.implementation_type,
            "location": self.location,
            "notes": self.notes,
        }

    @classmethod
    def from_row(cls, row) -> "PIImplementation":
        """Create from database row."""
        return cls(
            pi_id=row["pi_id"],
            implementation_date=row["implementation_date"],
            implementation_type=ImplementationType(row["implementation_type"])
            if row["implementation_type"]
            else None,
            location=row["location"],
            notes=row["notes"],
        )
