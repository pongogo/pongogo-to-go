# Test Pyramid Layer Definitions

**Issue**: [#368](https://github.com/pongogo/pongogo/issues/368) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document defines the test pyramid structure for pongogo-to-go, establishing clear boundaries between test layers with specific test targets for each.

**Core Principle**: Each layer has distinct purpose, speed, and isolation level.

---

## Test Pyramid Summary

```
                    ┌───────────┐
                    │    E2E    │  ~4 scenarios, slowest
                    │  (Docker) │  Full user workflows
                    └─────┬─────┘
                    ┌─────┴─────┐
                    │Integration│  ~15-20 tests
                    │  (Docker) │  Component interactions
                    └─────┬─────┘
              ┌───────────┴───────────┐
              │       Unit Tests      │  ~50+ tests, fastest
              │    (Direct Python)    │  Individual functions
              └───────────┬───────────┘
        ┌─────────────────┴─────────────────┐
        │         Pre-commit Hooks          │  Local, instant
        │  (Lint, Format, Type Check)       │  Quality gates
        └───────────────────────────────────┘
```

---

## Layer 1: Pre-commit Hooks (Local, Instant)

### Purpose
Catch code quality issues before commit. Fast feedback loop for developers.

### Tools

| Tool | Purpose | Config Location |
|------|---------|-----------------|
| `ruff` | Linting + formatting | `pyproject.toml` |
| `ruff format` | Code formatting | `pyproject.toml` |
| `mypy` | Type checking | `pyproject.toml` |

### Scope

**What's Checked**:
- Code formatting consistency
- Import sorting
- Common Python anti-patterns
- Type annotation correctness
- Unused imports/variables

**What's NOT Checked**:
- Runtime behavior
- Test execution
- Integration correctness

### Execution

```bash
# Runs automatically on git commit (via pre-commit hooks)
pre-commit run --all-files

# Manual execution
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

### Performance Target
- **Total time**: < 30 seconds
- **Blocking**: Yes (prevents commit on failure)

---

## Layer 2: Unit Tests (Docker, Fast)

### Purpose
Test individual functions and classes in isolation. Verify component correctness without external dependencies.

### Scope

**What's Tested**: Pure functions, class methods, data transformations, parsing logic.

**What's NOT Tested**: I/O operations, network calls, filesystem operations (mocked).

### Test Directory Structure

```
tests/
└── unit/
    ├── cli/
    │   ├── test_config.py
    │   ├── test_preferences.py
    │   ├── test_instructions.py
    │   └── test_discoveries.py
    └── mcp_server/
        ├── test_routing_engine.py
        ├── test_router.py
        ├── test_instruction_handler.py
        ├── engines/
        │   ├── test_durian_00.py
        │   ├── test_durian_05.py
        │   └── test_durian_051.py
        ├── discovery_system/
        │   ├── test_scanner.py
        │   └── test_database.py
        └── pi_system/
            ├── test_models.py
            ├── test_database.py
            └── test_operations.py
```

### Specific Test Targets

#### CLI Module (`src/cli/`)

| File | Test Focus | Priority |
|------|------------|----------|
| `config.py` | YAML parsing, config validation, defaults | High |
| `preferences.py` | Preference loading, validation, merging | High |
| `instructions.py` | Instruction file discovery, parsing | High |
| `discoveries.py` | Discovery data structures, filtering | Medium |
| `init_command.py` | Argument parsing (not filesystem ops) | Medium |
| `setup_mcp.py` | Config file generation logic | Medium |

#### MCP Server Module (`src/mcp_server/`)

| File | Test Focus | Priority |
|------|------------|----------|
| `routing_engine.py` | Engine interface, engine selection | High |
| `router.py` | Request routing logic, pattern matching | High |
| `instruction_handler.py` | Instruction loading, formatting | High |
| `config.py` | Server config parsing, validation | High |
| `engines/durian_*.py` | Scoring algorithms, ranking logic | High |
| `discovery_system/scanner.py` | File scanning patterns | Medium |
| `discovery_system/database.py` | SQLite operations | Medium |
| `pi_system/models.py` | Data models, validation | Medium |
| `pi_system/operations.py` | PI CRUD operations | Medium |

### Mock Strategy

| External Dependency | Mock Approach |
|---------------------|---------------|
| Filesystem | `tmp_path` fixture, in-memory |
| SQLite databases | In-memory `:memory:` databases |
| Environment variables | `monkeypatch` fixture |
| YAML files | String fixtures |

### Performance Target
- **Total time**: < 60 seconds
- **Individual test**: < 1 second
- **Parallelization**: Yes (`pytest-xdist`)

### Coverage Target
- **Line coverage**: ≥ 80%
- **Branch coverage**: ≥ 70%
- **Critical paths**: 100% (routing, config parsing)

---

## Layer 3: Integration Tests (Docker, Medium)

### Purpose
Test component interactions and workflows. Verify components work together correctly.

### Scope

**What's Tested**: Component integration, API contracts, database operations, file I/O.

**What's NOT Tested**: Full user workflows (E2E), external services.

### Test Directory Structure

```
tests/
└── integration/
    ├── test_init_workflow.py       # pongogo init creates correct structure
    ├── test_setup_mcp_workflow.py  # setup-mcp configures correctly
    ├── test_server_startup.py      # MCP server starts and responds
    ├── test_routing_flow.py        # Query → routing → instruction delivery
    ├── test_discovery_flow.py      # Discovery system full cycle
    └── test_pi_system_flow.py      # PI system full cycle
```

### Specific Test Scenarios

#### CLI Integration

| Scenario | Test | Validates |
|----------|------|-----------|
| Init creates structure | `test_init_workflow.py` | `pongogo init` creates `.pongogo/` correctly |
| Init with preferences | `test_init_workflow.py` | Respects `pongogo-preferences.yaml` |
| Setup MCP configures | `test_setup_mcp_workflow.py` | Updates Claude Code config correctly |

#### MCP Server Integration

| Scenario | Test | Validates |
|----------|------|-----------|
| Server starts | `test_server_startup.py` | FastMCP server accepts connections |
| Route instructions | `test_routing_flow.py` | Query → engine → instructions returned |
| Discovery works | `test_discovery_flow.py` | Scanner → database → query works |
| PI tracking | `test_pi_system_flow.py` | PI create → track → query cycle |

### Fixture Strategy

```python
# tests/integration/conftest.py

@pytest.fixture
def initialized_project(tmp_path):
    """Create a fully initialized pongogo project."""
    # Copy fixture files
    shutil.copytree(
        Path(__file__).parent.parent / "fixtures" / "initialized-project",
        tmp_path / "project"
    )
    return tmp_path / "project"

@pytest.fixture
def mcp_server_process(initialized_project):
    """Start MCP server as subprocess for integration tests."""
    # Start server pointing to initialized project
    process = subprocess.Popen(
        ["pongogo-server"],
        cwd=initialized_project,
        env={**os.environ, "PONGOGO_TEST_MODE": "1"}
    )
    yield process
    process.terminate()
```

### Performance Target
- **Total time**: < 3 minutes
- **Individual test**: < 30 seconds
- **Parallelization**: Limited (resource contention)

---

## Layer 4: E2E Tests (Docker, Slow)

### Purpose
Validate complete user workflows in isolated Docker environment. Ensure product works as users expect.

### Scope

**What's Tested**: Full user journeys from start to finish.

**What's NOT Tested**: Claude Code integration (uses mock MCP client).

### Test Directory Structure

```
tests/
└── e2e/
    ├── conftest.py                 # Docker container fixtures
    ├── test_learning_loop.py       # Implicit learning loop trigger
    ├── test_slash_commands.py      # /pongogo-retro, /pongogo-log, /pongogo-done
    └── test_full_workflows.py      # Complete project lifecycle
```

### Required Scenarios (from Core Loop Pattern)

All Pongogo intelligence flows follow: **Recognize → Increment → Artifact**

| Scenario | Flow | Test |
|----------|------|------|
| **Implicit Learning Loop** | init → work → "I'm done" → learning loop suggested | `test_learning_loop.py` |
| **Explicit Retro** | `/pongogo-retro` → questions → summary | `test_slash_commands.py` |
| **Work Logging** | `/pongogo-log` → format → entry created | `test_slash_commands.py` |
| **Completion Checklist** | `/pongogo-done` → checklist → confirmed | `test_slash_commands.py` |

### E2E Test Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Docker Test Container                        │
├────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐      ┌──────────────────────────────┐   │
│  │  Mock MCP Client │ ──── │  Pongogo MCP Server          │   │
│  │  (pytest)        │      │  (pongogo-server)            │   │
│  └──────────────────┘      └──────────────────────────────┘   │
│           │                            │                       │
│           ▼                            ▼                       │
│  ┌──────────────────┐      ┌──────────────────────────────┐   │
│  │  Test Assertions │      │  Test Project                │   │
│  │                  │      │  (.pongogo/, instructions/)  │   │
│  └──────────────────┘      └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

### Scenario Details

#### Scenario 1: Implicit Learning Loop

```python
# tests/e2e/test_learning_loop.py

def test_implicit_learning_loop_trigger(pongogo_server, mock_mcp_client):
    """
    Recognize: User says "I'm done" or similar completion phrase
    Increment: Counter tracks completion events
    Artifact: Learning loop suggestion returned
    """
    # Setup: Initialize project
    mock_mcp_client.call_tool("route_instructions", {
        "message": "pongogo init completed successfully"
    })

    # Trigger: User indicates completion
    response = mock_mcp_client.call_tool("route_instructions", {
        "message": "I'm done with this task"
    })

    # Assert: Learning loop suggested
    assert "learning loop" in response.lower() or \
           "/pongogo-retro" in response
```

#### Scenario 2: Explicit Slash Commands

```python
# tests/e2e/test_slash_commands.py

def test_pongogo_retro_flow(pongogo_server, mock_mcp_client):
    """Test /pongogo-retro produces structured retrospective."""
    response = mock_mcp_client.call_tool("route_instructions", {
        "message": "/pongogo-retro"
    })

    # Assert structured output
    assert "what went well" in response.lower()
    assert "what could improve" in response.lower()

def test_pongogo_log_flow(pongogo_server, mock_mcp_client):
    """Test /pongogo-log creates work log entry."""
    response = mock_mcp_client.call_tool("route_instructions", {
        "message": "/pongogo-log"
    })

    # Assert work log format
    assert "work log" in response.lower()

def test_pongogo_done_flow(pongogo_server, mock_mcp_client):
    """Test /pongogo-done shows completion checklist."""
    response = mock_mcp_client.call_tool("route_instructions", {
        "message": "/pongogo-done"
    })

    # Assert checklist content
    assert "checklist" in response.lower()
```

### Performance Target
- **Total time**: < 5 minutes
- **Individual scenario**: < 60 seconds
- **Parallelization**: No (sequential for reliability)

---

## Coverage Strategy

### Per-Layer Targets

| Layer | Coverage Target | Enforcement |
|-------|-----------------|-------------|
| Unit | ≥ 80% lines, ≥ 70% branches | CI gate |
| Integration | N/A (scenario-based) | All scenarios pass |
| E2E | N/A (workflow-based) | All workflows pass |

### Critical Path Coverage (100% Required)

These paths must have complete test coverage:

1. **Config parsing** - `src/cli/config.py`, `src/mcp_server/config.py`
2. **Routing engine** - `src/mcp_server/routing_engine.py`, `src/mcp_server/router.py`
3. **Instruction delivery** - `src/mcp_server/instruction_handler.py`

### Coverage Reporting

```bash
# Generate coverage report
pytest tests/unit tests/integration --cov=src --cov-report=html --cov-report=xml

# Coverage thresholds in CI
pytest --cov=src --cov-fail-under=80
```

---

## Test Execution Order

### Local Development

```bash
# Quick feedback (< 2 min)
make test-unit

# Full validation (< 10 min)
make test
```

### CI Pipeline

```
Pre-commit → Unit → Integration → E2E
    ↓           ↓         ↓          ↓
  30s         60s       3min       5min
```

**Gate Policy**: Each layer must pass before proceeding to next.

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `tests/unit/` directory structure with test files
- [ ] Create `tests/integration/` directory with workflow tests
- [ ] Create `tests/e2e/` directory with scenario tests
- [ ] Implement unit tests for all Priority High targets
- [ ] Implement integration tests for all scenarios
- [ ] Implement E2E tests for 4 core scenarios
- [ ] Configure pytest coverage thresholds
- [ ] Add Makefile targets for each layer

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Docker Environment: `docs/design/docker_test_environment.md`
- Mock MCP Client: See #369 (to be created)
