# Ground Truth System Design

**Issue**: [#370](https://github.com/pongogo/pongogo/issues/370) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document specifies the ground truth system for pongogo-to-go routing accuracy testing. Ground truth enables regression testing to ensure routing changes don't degrade quality.

**Core Purpose**: Verify that user queries route to the correct instructions with measurable accuracy.

---

## Ground Truth Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Ground Truth Test Flow                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐                                                  │
│  │  ground_truth.json │  Load test cases                                 │
│  │  (~50-100 events)  │                                                  │
│  └─────────┬──────────┘                                                  │
│            │                                                             │
│            ▼                                                             │
│  ┌────────────────────┐      ┌────────────────────────────────────┐     │
│  │  For each event:   │      │  MockMCPClient                     │     │
│  │  - query           │ ───▶ │  route_instructions(query)         │     │
│  │  - expected[]      │      └────────────────────────────────────┘     │
│  └────────────────────┘                    │                             │
│                                            ▼                             │
│                               ┌────────────────────────────────────┐    │
│                               │  Compare:                          │    │
│                               │  - actual_instructions             │    │
│                               │  - expected_instructions           │    │
│                               └────────────────────────────────────┘    │
│                                            │                             │
│                                            ▼                             │
│                               ┌────────────────────────────────────┐    │
│                               │  Calculate Metrics:                │    │
│                               │  - Precision, Recall, F1           │    │
│                               │  - Per-category accuracy           │    │
│                               └────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Format: JSON

### Why JSON (Not SQLite)

| Consideration | JSON | SQLite |
|---------------|------|--------|
| Human readability | High - easy to review/edit | Low - requires tooling |
| Version control | Excellent - diff-friendly | Poor - binary diffs |
| Size (~100 events) | Negligible (~50KB) | Overkill |
| Query capability | Unnecessary for tests | Unnecessary for tests |
| Portability | Universal | Universal |

**Decision**: JSON for simplicity and reviewability at this scale.

### File Location

```
tests/
└── fixtures/
    └── ground-truth/
        ├── ground_truth.json       # Primary ground truth dataset
        ├── README.md               # Dataset documentation
        └── schemas/
            └── ground_truth.schema.json  # JSON Schema for validation
```

---

## Event Structure

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Ground Truth Dataset",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "description": "Dataset version (semver)"
    },
    "created": {
      "type": "string",
      "format": "date",
      "description": "Dataset creation date"
    },
    "description": {
      "type": "string",
      "description": "Dataset purpose and scope"
    },
    "events": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/GroundTruthEvent"
      }
    }
  },
  "required": ["version", "events"],
  "definitions": {
    "GroundTruthEvent": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^GT-[0-9]{3}$",
          "description": "Unique event ID (GT-001, GT-002, ...)"
        },
        "query": {
          "type": "string",
          "description": "User query/message to route"
        },
        "category": {
          "type": "string",
          "enum": [
            "_pongogo_core",
            "agentic_workflows",
            "architecture",
            "development",
            "devops",
            "github_integration",
            "project_management",
            "quality",
            "safety_prevention",
            "software_engineering",
            "testing",
            "trust_execution",
            "validation"
          ],
          "description": "Primary instruction category"
        },
        "expected_instructions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "minItems": 1,
          "description": "Expected instruction file names (without .instructions.md)"
        },
        "context": {
          "type": "object",
          "description": "Optional conversation context",
          "properties": {
            "prior_topic": { "type": "string" },
            "task_type": { "type": "string" }
          }
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Test classification tags"
        },
        "notes": {
          "type": "string",
          "description": "Optional notes about this test case"
        }
      },
      "required": ["id", "query", "category", "expected_instructions"]
    }
  }
}
```

### Example Event

```json
{
  "id": "GT-001",
  "query": "how do I conduct a learning loop?",
  "category": "_pongogo_core",
  "expected_instructions": ["learning_loop"],
  "tags": ["core-loop", "explicit-request"],
  "notes": "Direct request for learning loop instruction"
}
```

---

## Category Taxonomy

### Seeded Instruction Categories

Based on analysis of `pongogo-to-go/instructions/`:

| Category | Files | Primary Use Cases |
|----------|-------|-------------------|
| `_pongogo_core` | 9 | Learning loops, issue management, PI tracking, work logging |
| `agentic_workflows` | 4 | Decision making, compliance, multi-pass analysis |
| `architecture` | 1 | Repository organization |
| `development` | 1 | Token/context management |
| `devops` | 2 | Audit logging, observability |
| `github_integration` | 2 | GitHub API, sub-issues |
| `project_management` | 6 | Scope, work logging, time-free PM |
| `quality` | 2 | PR workflow, environment config |
| `safety_prevention` | 3 | Validation-first, git safety |
| `software_engineering` | 3 | Commits, git safety, Python |
| `testing` | 1 | Observability testing |
| `trust_execution` | 3 | Trust-based development, feature dev |
| `validation` | 3 | Verification, deterministic validation |

### Test Tags

Tags classify test cases for analysis and filtering:

| Tag | Description |
|-----|-------------|
| `core-loop` | Tests core Pongogo loops (learning, work logging, PI) |
| `explicit-request` | User directly asks for something |
| `implicit-trigger` | Routing triggered by context/pattern |
| `slash-command` | Tests `/pongogo-*` command routing |
| `multi-instruction` | Expects multiple instructions returned |
| `edge-case` | Tests boundary conditions |
| `category-overlap` | Query could match multiple categories |

---

## Ground Truth Events

### Target Distribution

**Total Events**: 50-100

**Distribution by Priority**:

| Priority | Category | Target Events | Rationale |
|----------|----------|---------------|-----------|
| High | `_pongogo_core` | 20-25 | Core functionality, most critical |
| High | `project_management` | 10-12 | Common PM queries |
| Medium | `software_engineering` | 8-10 | Common development queries |
| Medium | `safety_prevention` | 6-8 | Safety-critical routing |
| Medium | `agentic_workflows` | 6-8 | Agent behavior queries |
| Low | Others | 10-15 | Coverage of remaining categories |

### Sample Events by Category

#### _pongogo_core (20-25 events)

```json
{
  "id": "GT-001",
  "query": "how do I conduct a learning loop?",
  "category": "_pongogo_core",
  "expected_instructions": ["learning_loop"],
  "tags": ["core-loop", "explicit-request"]
},
{
  "id": "GT-002",
  "query": "I'm done with this task",
  "category": "_pongogo_core",
  "expected_instructions": ["learning_loop"],
  "tags": ["core-loop", "implicit-trigger"]
},
{
  "id": "GT-003",
  "query": "/pongogo-retro",
  "category": "_pongogo_core",
  "expected_instructions": ["learning_loop"],
  "tags": ["core-loop", "slash-command"]
},
{
  "id": "GT-004",
  "query": "how should I close this issue?",
  "category": "_pongogo_core",
  "expected_instructions": ["issue_closure"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-005",
  "query": "add a work log entry",
  "category": "_pongogo_core",
  "expected_instructions": ["work_logging"],
  "tags": ["core-loop", "explicit-request"]
},
{
  "id": "GT-006",
  "query": "/pongogo-log",
  "category": "_pongogo_core",
  "expected_instructions": ["work_logging"],
  "tags": ["core-loop", "slash-command"]
},
{
  "id": "GT-007",
  "query": "I noticed a pattern that could be improved",
  "category": "_pongogo_core",
  "expected_instructions": ["pi_tracking"],
  "tags": ["core-loop", "implicit-trigger"]
},
{
  "id": "GT-008",
  "query": "how do I create a new issue?",
  "category": "_pongogo_core",
  "expected_instructions": ["issue_creation"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-009",
  "query": "what's the status of this issue?",
  "category": "_pongogo_core",
  "expected_instructions": ["issue_status"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-010",
  "query": "there was an incident in production",
  "category": "_pongogo_core",
  "expected_instructions": ["incident_handling"],
  "tags": ["implicit-trigger"]
}
```

#### project_management (10-12 events)

```json
{
  "id": "GT-020",
  "query": "how do I estimate this task?",
  "category": "project_management",
  "expected_instructions": ["time_free_project_management"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-021",
  "query": "this task is growing beyond the original scope",
  "category": "project_management",
  "expected_instructions": ["scope_creep_prevention"],
  "tags": ["implicit-trigger"]
},
{
  "id": "GT-022",
  "query": "what goes in a weekly work log summary?",
  "category": "project_management",
  "expected_instructions": ["work_log_weekly_summary"],
  "tags": ["explicit-request"]
}
```

#### software_engineering (8-10 events)

```json
{
  "id": "GT-030",
  "query": "how should I format this commit message?",
  "category": "software_engineering",
  "expected_instructions": ["commit_message_format"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-031",
  "query": "is it safe to force push?",
  "category": "software_engineering",
  "expected_instructions": ["git_safety"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-032",
  "query": "writing a Python script for data processing",
  "category": "software_engineering",
  "expected_instructions": ["python_script_development"],
  "tags": ["implicit-trigger"]
}
```

#### safety_prevention (6-8 events)

```json
{
  "id": "GT-040",
  "query": "should I validate before executing?",
  "category": "safety_prevention",
  "expected_instructions": ["validation_first_execution"],
  "tags": ["explicit-request"]
},
{
  "id": "GT-041",
  "query": "about to run a destructive command",
  "category": "safety_prevention",
  "expected_instructions": ["git_safety", "systematic_prevention_framework"],
  "tags": ["multi-instruction", "implicit-trigger"]
}
```

---

## Evaluation Metrics

### Primary Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Precision** | TP / (TP + FP) | ≥ 0.80 |
| **Recall** | TP / (TP + FN) | ≥ 0.85 |
| **F1 Score** | 2 × (P × R) / (P + R) | ≥ 0.82 |

### Definitions

- **True Positive (TP)**: Expected instruction correctly returned
- **False Positive (FP)**: Unexpected instruction returned
- **False Negative (FN)**: Expected instruction not returned

### Per-Event Scoring

For each ground truth event:

```python
def score_event(expected: list[str], actual: list[str]) -> dict:
    """Score a single routing event."""
    expected_set = set(expected)
    actual_set = set(actual)

    tp = len(expected_set & actual_set)
    fp = len(actual_set - expected_set)
    fn = len(expected_set - actual_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn
    }
```

### Aggregate Scoring

```python
def aggregate_scores(event_scores: list[dict]) -> dict:
    """Calculate aggregate metrics across all events."""
    total_tp = sum(s["tp"] for s in event_scores)
    total_fp = sum(s["fp"] for s in event_scores)
    total_fn = sum(s["fn"] for s in event_scores)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total_events": len(event_scores),
        "perfect_matches": sum(1 for s in event_scores if s["f1"] == 1.0)
    }
```

---

## pytest Integration

### Test Module

```python
# tests/integration/test_routing_accuracy.py
"""Routing accuracy tests using ground truth dataset."""

import json
import pytest
from pathlib import Path

from tests.helpers.mock_mcp_client import MockMCPClient


@pytest.fixture(scope="module")
def ground_truth() -> dict:
    """Load ground truth dataset."""
    path = Path(__file__).parent.parent / "fixtures" / "ground-truth" / "ground_truth.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth_events(ground_truth) -> list[dict]:
    """Extract events from ground truth."""
    return ground_truth["events"]


class TestRoutingAccuracy:
    """Test routing accuracy against ground truth."""

    @pytest.mark.asyncio
    async def test_aggregate_accuracy(
        self,
        mock_mcp_client: MockMCPClient,
        ground_truth_events: list[dict]
    ):
        """Verify aggregate routing accuracy meets thresholds."""
        scores = []

        for event in ground_truth_events:
            response = await mock_mcp_client.route_instructions(
                message=event["query"],
                context=event.get("context")
            )

            # Extract instruction names from response
            actual = self._extract_instruction_names(response.content)
            expected = event["expected_instructions"]

            score = self._score_event(expected, actual)
            scores.append({**score, "id": event["id"]})

        aggregate = self._aggregate_scores(scores)

        # Assert thresholds
        assert aggregate["precision"] >= 0.80, \
            f"Precision {aggregate['precision']:.2f} below threshold 0.80"
        assert aggregate["recall"] >= 0.85, \
            f"Recall {aggregate['recall']:.2f} below threshold 0.85"
        assert aggregate["f1"] >= 0.82, \
            f"F1 {aggregate['f1']:.2f} below threshold 0.82"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_id", [
        "GT-001", "GT-002", "GT-003", "GT-004", "GT-005"  # Critical events
    ])
    async def test_critical_events(
        self,
        mock_mcp_client: MockMCPClient,
        ground_truth_events: list[dict],
        event_id: str
    ):
        """Test critical events individually."""
        event = next(e for e in ground_truth_events if e["id"] == event_id)

        response = await mock_mcp_client.route_instructions(
            message=event["query"],
            context=event.get("context")
        )

        actual = self._extract_instruction_names(response.content)
        expected = set(event["expected_instructions"])

        # Critical events must have perfect recall
        assert expected.issubset(set(actual)), \
            f"Event {event_id}: Missing expected instructions. " \
            f"Expected: {expected}, Got: {actual}"

    def _extract_instruction_names(self, content: str) -> list[str]:
        """Extract instruction file names from routing response."""
        # Implementation depends on response format
        # Placeholder - actual implementation parses response
        return []

    def _score_event(self, expected: list, actual: list) -> dict:
        """Score single event (see Evaluation Metrics section)."""
        # Implementation from Evaluation Metrics section
        pass

    def _aggregate_scores(self, scores: list) -> dict:
        """Aggregate scores (see Evaluation Metrics section)."""
        # Implementation from Evaluation Metrics section
        pass
```

### CI Integration

```yaml
# .github/workflows/ci.yml (excerpt)
jobs:
  routing-accuracy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run routing accuracy tests
        run: |
          docker run --rm pongogo-test \
            pytest tests/integration/test_routing_accuracy.py -v \
            --tb=short

      - name: Check accuracy thresholds
        if: failure()
        run: |
          echo "::error::Routing accuracy below thresholds. Check test output."
```

---

## Ground Truth Maintenance

### Update Process

1. **When to Update**:
   - New instruction files added
   - Existing instructions renamed/removed
   - Routing behavior intentionally changed
   - New query patterns discovered

2. **Update Workflow**:
   ```bash
   # 1. Edit ground_truth.json
   vim tests/fixtures/ground-truth/ground_truth.json

   # 2. Validate schema
   python -c "import json; json.load(open('tests/fixtures/ground-truth/ground_truth.json'))"

   # 3. Run accuracy tests
   pytest tests/integration/test_routing_accuracy.py -v

   # 4. Commit with context
   git add tests/fixtures/ground-truth/
   git commit -m "Update ground truth: [reason]"
   ```

3. **Version Bumping**:
   - Patch: Fix incorrect expectations
   - Minor: Add new events
   - Major: Restructure or redefine categories

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `tests/fixtures/ground-truth/` directory
- [ ] Create `ground_truth.schema.json` for validation
- [ ] Create `ground_truth.json` with initial 50-60 events
- [ ] Create `tests/integration/test_routing_accuracy.py`
- [ ] Implement `_extract_instruction_names()` based on response format
- [ ] Implement scoring functions
- [ ] Add ground truth validation to CI
- [ ] Document event creation process in README.md

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Mock MCP Client: `docs/design/mock_mcp_client.md`
- Super Pongogo Eval: `scripts/evaluate_routing.py` (pattern reference)
- Seeded Instructions: `pongogo-to-go/instructions/`
