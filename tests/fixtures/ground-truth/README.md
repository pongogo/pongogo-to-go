# Ground Truth Dataset

This directory contains the ground truth dataset for routing accuracy testing.

## Purpose

Ground truth enables regression testing to ensure routing changes don't degrade quality. Each event maps a user query to expected instruction files.

## Files

```
ground-truth/
├── ground_truth.json           # Primary dataset (60 events)
├── README.md                   # This file
└── schemas/
    └── ground_truth.schema.json  # JSON Schema for validation
```

## Event Structure

Each event contains:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (GT-001, GT-002, ...) |
| `query` | Yes | User message to route |
| `category` | Yes | Primary instruction category |
| `expected_instructions` | Yes | List of expected instruction file names |
| `context` | No | Optional conversation context |
| `tags` | No | Classification tags for filtering |
| `notes` | No | Notes about the test case |

## Categories

| Category | Event Count | Coverage |
|----------|-------------|----------|
| `_pongogo_core` | 20 | Core loops: learning, work logging, issues |
| `project_management` | 8 | PM workflows, scope, summaries |
| `software_engineering` | 6 | Git, commits, Python |
| `safety_prevention` | 5 | Validation, prevention |
| `agentic_workflows` | 4 | Agent behavior |
| `quality` | 2 | PRs, environment |
| `github_integration` | 2 | GitHub API, sub-issues |
| `trust_execution` | 3 | Trust-based development |
| `validation` | 3 | Verification |
| `devops` | 2 | Observability, audit |
| `architecture` | 1 | Repository organization |
| `development` | 1 | Token management |
| `testing` | 1 | Observability testing |

## Tags

| Tag | Description |
|-----|-------------|
| `core-loop` | Tests core Pongogo loops |
| `explicit-request` | User directly asks for something |
| `implicit-trigger` | Routing triggered by context/pattern |
| `slash-command` | Tests `/pongogo-*` command routing |
| `multi-instruction` | Expects multiple instructions returned |
| `edge-case` | Tests boundary conditions |

## Accuracy Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Precision | >= 0.80 | Avoid returning irrelevant instructions |
| Recall | >= 0.85 | Return all expected instructions |
| F1 Score | >= 0.82 | Balanced accuracy |

## Updating Ground Truth

### When to Update

- New instruction files added
- Existing instructions renamed/removed
- Routing behavior intentionally changed
- New query patterns discovered

### Update Process

```bash
# 1. Edit ground_truth.json
vim tests/fixtures/ground-truth/ground_truth.json

# 2. Validate JSON syntax
python -c "import json; json.load(open('tests/fixtures/ground-truth/ground_truth.json'))"

# 3. Run accuracy tests
pytest tests/integration/test_routing_accuracy.py -v

# 4. Commit with context
git add tests/fixtures/ground-truth/
git commit -m "Update ground truth: [reason]"
```

### Version Bumping

- **Patch**: Fix incorrect expectations
- **Minor**: Add new events
- **Major**: Restructure categories or redefine schema

## Running Tests

```bash
# Run all routing accuracy tests
pytest tests/integration/test_routing_accuracy.py -v

# Run with detailed output
pytest tests/integration/test_routing_accuracy.py -v --tb=long

# Run critical events only
pytest tests/integration/test_routing_accuracy.py -v -k "critical"
```
