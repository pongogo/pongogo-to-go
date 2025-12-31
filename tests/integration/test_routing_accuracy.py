"""Routing accuracy tests using ground truth dataset.

These tests verify that the routing system correctly maps user queries
to expected instruction files, with measurable precision, recall, and F1 scores.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.helpers.mock_mcp_client import MockMCPClient


# =============================================================================
# Constants
# =============================================================================

# Accuracy thresholds
PRECISION_THRESHOLD = 0.80
RECALL_THRESHOLD = 0.85
F1_THRESHOLD = 0.82

# Critical events that must have perfect recall
CRITICAL_EVENT_IDS = [
    "GT-001",  # learning loop - explicit
    "GT-002",  # learning loop - implicit
    "GT-003",  # learning loop - slash command
    "GT-004",  # issue closure
    "GT-005",  # work logging
]


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class EventScore:
    """Score for a single ground truth event."""

    event_id: str
    expected: set[str]
    actual: set[str]
    tp: int = 0  # True positives
    fp: int = 0  # False positives
    fn: int = 0  # False negatives
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    def __post_init__(self) -> None:
        """Calculate metrics from expected/actual sets."""
        self.tp = len(self.expected & self.actual)
        self.fp = len(self.actual - self.expected)
        self.fn = len(self.expected - self.actual)

        self.precision = (
            self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0
        )
        self.recall = self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0
        self.f1 = (
            2 * self.precision * self.recall / (self.precision + self.recall)
            if (self.precision + self.recall) > 0
            else 0.0
        )

    @property
    def is_perfect(self) -> bool:
        """Check if this is a perfect match."""
        return self.f1 == 1.0


@dataclass
class AggregateScore:
    """Aggregate scores across all events."""

    event_scores: list[EventScore] = field(default_factory=list)
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    total_events: int = 0
    perfect_matches: int = 0

    def __post_init__(self) -> None:
        """Calculate aggregate metrics from event scores."""
        if not self.event_scores:
            return

        total_tp = sum(s.tp for s in self.event_scores)
        total_fp = sum(s.fp for s in self.event_scores)
        total_fn = sum(s.fn for s in self.event_scores)

        self.precision = (
            total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        )
        self.recall = (
            total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        )
        self.f1 = (
            2 * self.precision * self.recall / (self.precision + self.recall)
            if (self.precision + self.recall) > 0
            else 0.0
        )

        self.total_events = len(self.event_scores)
        self.perfect_matches = sum(1 for s in self.event_scores if s.is_perfect)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def ground_truth_path() -> Path:
    """Return path to ground truth dataset."""
    return (
        Path(__file__).parent.parent / "fixtures" / "ground-truth" / "ground_truth.json"
    )


@pytest.fixture(scope="module")
def ground_truth(ground_truth_path: Path) -> dict[str, Any]:
    """Load ground truth dataset."""
    with open(ground_truth_path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth_events(ground_truth: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract events from ground truth."""
    return ground_truth["events"]


# =============================================================================
# Helper Functions
# =============================================================================


def extract_instruction_names(content: str | None) -> list[str]:
    """Extract instruction file names from routing response.

    Parses the response content to find instruction file references.
    Handles various response formats.

    Args:
        content: Response content from route_instructions call

    Returns:
        List of instruction names (without .instructions.md suffix)
    """
    if not content:
        return []

    # Pattern to match instruction file names
    # Matches: word.instructions.md or word_word.instructions.md
    pattern = r"([a-z_]+)\.instructions\.md"
    matches = re.findall(pattern, content.lower())

    # Also try to match instruction names mentioned without extension
    # This handles cases where the response just mentions the instruction name
    name_pattern = r"\b([a-z_]+)_instruction[s]?\b"
    name_matches = re.findall(name_pattern, content.lower())

    # Combine and deduplicate
    all_matches = list(set(matches + name_matches))

    return all_matches


def score_event(
    event_id: str,
    expected: list[str],
    actual: list[str],
) -> EventScore:
    """Score a single routing event.

    Args:
        event_id: Ground truth event ID
        expected: List of expected instruction names
        actual: List of actual instruction names from routing

    Returns:
        EventScore with metrics
    """
    return EventScore(
        event_id=event_id,
        expected=set(expected),
        actual=set(actual),
    )


def aggregate_scores(event_scores: list[EventScore]) -> AggregateScore:
    """Calculate aggregate metrics across all events.

    Args:
        event_scores: List of individual event scores

    Returns:
        AggregateScore with overall metrics
    """
    return AggregateScore(event_scores=event_scores)


# =============================================================================
# Test Classes
# =============================================================================

# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestRoutingAccuracy:
    """Test routing accuracy against ground truth."""

    async def test_aggregate_accuracy(
        self,
        mock_mcp_client: MockMCPClient,
        ground_truth_events: list[dict[str, Any]],
    ) -> None:
        """Verify aggregate routing accuracy meets thresholds."""
        scores = []

        for event in ground_truth_events:
            response = await mock_mcp_client.route_instructions(
                message=event["query"],
                context=event.get("context"),
            )

            # Extract instruction names from response
            actual = extract_instruction_names(response.content)
            expected = event["expected_instructions"]

            score = score_event(event["id"], expected, actual)
            scores.append(score)

        aggregate = aggregate_scores(scores)

        # Report detailed results
        print(f"\n{'='*60}")
        print("Routing Accuracy Results")
        print(f"{'='*60}")
        print(f"Total events: {aggregate.total_events}")
        print(f"Perfect matches: {aggregate.perfect_matches}")
        print(f"Precision: {aggregate.precision:.2%}")
        print(f"Recall: {aggregate.recall:.2%}")
        print(f"F1 Score: {aggregate.f1:.2%}")
        print(f"{'='*60}")

        # Report failures
        failed = [s for s in scores if not s.is_perfect]
        if failed:
            print(f"\nFailed events ({len(failed)}):")
            for s in failed[:10]:  # Limit to first 10
                print(
                    f"  {s.event_id}: P={s.precision:.2f} R={s.recall:.2f} F1={s.f1:.2f}"
                )
                print(f"    Expected: {s.expected}")
                print(f"    Actual: {s.actual}")

        # Assert thresholds
        assert (
            aggregate.precision >= PRECISION_THRESHOLD
        ), f"Precision {aggregate.precision:.2%} below threshold {PRECISION_THRESHOLD:.0%}"
        assert (
            aggregate.recall >= RECALL_THRESHOLD
        ), f"Recall {aggregate.recall:.2%} below threshold {RECALL_THRESHOLD:.0%}"
        assert (
            aggregate.f1 >= F1_THRESHOLD
        ), f"F1 {aggregate.f1:.2%} below threshold {F1_THRESHOLD:.0%}"

    @pytest.mark.parametrize("event_id", CRITICAL_EVENT_IDS)
    async def test_critical_events(
        self,
        mock_mcp_client: MockMCPClient,
        ground_truth_events: list[dict[str, Any]],
        event_id: str,
    ) -> None:
        """Test critical events individually - must have perfect recall."""
        event = next((e for e in ground_truth_events if e["id"] == event_id), None)
        assert event is not None, f"Critical event {event_id} not found in ground truth"

        response = await mock_mcp_client.route_instructions(
            message=event["query"],
            context=event.get("context"),
        )

        actual = set(extract_instruction_names(response.content))
        expected = set(event["expected_instructions"])

        # Critical events must have perfect recall (all expected found)
        assert expected.issubset(actual), (
            f"Event {event_id}: Missing expected instructions. "
            f"Expected: {expected}, Got: {actual}"
        )


class TestGroundTruthDataset:
    """Tests for ground truth dataset validity."""

    def test_dataset_has_events(
        self, ground_truth_events: list[dict[str, Any]]
    ) -> None:
        """Verify dataset contains events."""
        assert (
            len(ground_truth_events) >= 50
        ), f"Expected at least 50 events, got {len(ground_truth_events)}"

    def test_event_ids_unique(self, ground_truth_events: list[dict[str, Any]]) -> None:
        """Verify all event IDs are unique."""
        ids = [e["id"] for e in ground_truth_events]
        assert len(ids) == len(set(ids)), "Duplicate event IDs found"

    def test_event_ids_sequential(
        self, ground_truth_events: list[dict[str, Any]]
    ) -> None:
        """Verify event IDs follow GT-NNN pattern."""
        for event in ground_truth_events:
            assert re.match(
                r"^GT-\d{3}$", event["id"]
            ), f"Invalid event ID format: {event['id']}"

    def test_critical_events_exist(
        self, ground_truth_events: list[dict[str, Any]]
    ) -> None:
        """Verify all critical events exist in dataset."""
        event_ids = {e["id"] for e in ground_truth_events}
        for critical_id in CRITICAL_EVENT_IDS:
            assert (
                critical_id in event_ids
            ), f"Critical event {critical_id} missing from dataset"


class TestCategoryDistribution:
    """Tests for category coverage in ground truth."""

    def test_all_categories_covered(
        self,
        ground_truth_events: list[dict[str, Any]],
    ) -> None:
        """Verify all major categories have at least one event."""
        required_categories = {
            "_pongogo_core",
            "project_management",
            "software_engineering",
            "safety_prevention",
            "agentic_workflows",
        }

        covered = {e["category"] for e in ground_truth_events}
        missing = required_categories - covered

        assert not missing, f"Missing required categories: {missing}"

    def test_pongogo_core_has_sufficient_events(
        self,
        ground_truth_events: list[dict[str, Any]],
    ) -> None:
        """Verify _pongogo_core has high priority coverage."""
        core_events = [
            e for e in ground_truth_events if e["category"] == "_pongogo_core"
        ]
        assert (
            len(core_events) >= 15
        ), f"Expected at least 15 _pongogo_core events, got {len(core_events)}"
