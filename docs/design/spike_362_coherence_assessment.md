# Spike #362 Coherence Assessment

**Assessment Date**: 2025-12-30
**Spike**: #362 (e2e_test_harness_architecture)
**Implementation Tasks**: #374, #375, #376, #377, #378, #379

---

## Purpose

Birds-eye review of the 6 design documents produced by Spike #362 to ensure coherent implementation across all sub-tasks.

---

## Design Documents Reviewed

| Doc | Focus | Implementation |
|-----|-------|----------------|
| `docker_test_environment.md` | Container config, fixtures, lifecycle | #374 |
| `test_pyramid_layers.md` | Test structure, coverage targets | #375 |
| `mock_mcp_client.md` | MockMCPClient class, JSON-RPC | #376 |
| `ground_truth_system.md` | Routing accuracy testing | #377 |
| `precommit_configuration.md` | Pre-commit hooks, ruff, mypy | #378 |
| `cicd_workflow_specifications.md` | GitHub Actions workflows | #379 |

---

## Cross-Document Alignment Matrix

| Doc A | Doc B | Status | Notes |
|-------|-------|--------|-------|
| docker_test_environment | cicd_workflows | **ALIGNED** | Same Dockerfile path (`tests/Dockerfile`), same target (`test`) |
| docker_test_environment | test_pyramid | **ALIGNED** | Consistent fixture paths, scope patterns |
| mock_mcp_client | test_pyramid | **ALIGNED** | MockMCPClient used correctly in E2E scenarios |
| mock_mcp_client | ground_truth | **ALIGNED** | `route_instructions()` params match event fields |
| precommit_configuration | cicd_workflows | **ALIGNED** | CI runs same pre-commit hooks |
| test_pyramid | cicd_workflows | **ALIGNED** | 80% coverage threshold, execution order |
| ground_truth | cicd_workflows | **ALIGNED** | Routing tests run in integration phase |

---

## Gaps Identified

### Gap 1: Instruction Name Extraction (Minor)

**Location**: `ground_truth_system.md` → `_extract_instruction_names()`

**Issue**: The function is marked as placeholder with comment "Implementation depends on response format"

**Impact**: #377 implementer needs to know the MCP response format

**Resolution**: MockMCPClient already defines `MCPResponse.content` structure. Implementation should parse instruction file names from the text content returned by `route_instructions`.

**Action**: Add implementation note to #377 referencing `mock_mcp_client.md` response format.

---

### Gap 2: Python Version Clarification (Minor)

**Location**: Cross-cutting across documents

**Issue**: Inconsistent Python version references:
- `precommit_configuration.md`: target-version = "py310"
- `docker_test_environment.md`: `FROM python:3.11-slim`
- `cicd_workflow_specifications.md`: mentions 3.10, 3.11, 3.12

**Impact**: Confusion about minimum supported version

**Resolution**:
- **Minimum**: Python 3.10 (for compatibility)
- **CI/Docker**: Python 3.11 (current stable)
- **Tested**: 3.10, 3.11, 3.12 (via matrix when needed)

**Action**: No change needed - 3.10 is minimum, 3.11 is default in Docker. Pre-commit targets minimum.

---

### Gap 3: CI Matrix Strategy (Clarification)

**Location**: `cicd_workflow_specifications.md`

**Issue**: Document shows matrix strategy example but actual workflow uses single Python version

**Current**: Runs on Python 3.11 only
**Alternative**: Full matrix across 3.10, 3.11, 3.12

**Resolution**: Single version is intentional for faster CI. Matrix can be added later if compatibility issues arise. Document intent is correct.

**Action**: None - design is intentional.

---

## Confirmed Alignments

### 1. Dockerfile Structure
- Location: `tests/Dockerfile`
- Stages: `base` (production), `test` (dev deps)
- Consistent across docker_test_environment and cicd_workflows

### 2. Fixture Organization
```
tests/
├── fixtures/
│   ├── minimal-project/
│   ├── initialized-project/
│   ├── sample-instructions/
│   └── ground-truth/
├── unit/
├── integration/
└── e2e/
```
- Consistent across test_pyramid and docker_test_environment

### 3. Coverage Thresholds
- Line: ≥ 80%
- Branch: ≥ 70%
- Consistent across test_pyramid and cicd_workflows

### 4. Test Execution Order
```
Pre-commit → Build Image → Unit + Integration (parallel) → E2E
```
- Consistent across test_pyramid, precommit_configuration, and cicd_workflows

### 5. MockMCPClient Integration
- Async context manager pattern
- JSON-RPC 2.0 over stdio
- `route_instructions(message, context, limit)` signature
- Consistent across mock_mcp_client, test_pyramid, and ground_truth

### 6. Pre-commit Tools
- ruff (lint + format)
- mypy (type check)
- Consistent across precommit_configuration and cicd_workflows

---

## Implementation Dependencies

```
#378 (pre-commit) ─────────────────────────────────────────────┐
                                                               │
#374 (docker) ──┬──────────────────────────────────────────────┤
                │                                               │
                ├──> #375 (test structure) ──┐                 │
                │                            │                 │
                └──> #376 (mock client) ─────┼──> #379 (CI/CD) │
                                             │                 │
#377 (ground truth) ─────────────────────────┘                 │
                                                               │
All merge into #379 which orchestrates the complete pipeline ──┘
```

**Recommended Implementation Order**:
1. **#378** (pre-commit) - Independent, can start immediately
2. **#374** (docker) - Foundation for all tests
3. **#375** (test structure) - Depends on #374 for container
4. **#376** (mock client) - Depends on #374 for container
5. **#377** (ground truth) - Depends on #376 for client
6. **#379** (CI/CD) - Orchestrates all, should be last

---

## Coherence Verdict

**Status**: Ready for Implementation

**Summary**: The 6 design documents are well-aligned with no major conflicts. Minor gaps identified have clear resolutions. Implementation can proceed with the recommended order.

**Confidence**: HIGH - Cross-references verified, interfaces aligned, no blocking issues.

---

## Updates to Implementation Tasks

### #377 (implement_ground_truth_system)

Add to description:
> **Implementation Note**: For `_extract_instruction_names()`, parse instruction file names from `MCPResponse.content` text. See `mock_mcp_client.md` for response format. Instruction names typically appear in the routing response content.

---

**Created**: 2025-12-30
**Author**: Claude (Spike #362 completion review)
