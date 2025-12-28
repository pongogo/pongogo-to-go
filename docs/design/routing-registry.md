# Routing Registry

**Purpose**: Define the taxonomy of routing domains and keywords used by Pongogo's instruction routing system.

**Philosophy**: Internal and external Pongogo should not diverge. This registry ensures consistent routing behavior across all installations.

---

## Overview

The routing registry defines how user messages are matched to instruction files. Each instruction file declares its routing metadata in YAML frontmatter, and the routing engine uses this registry to resolve matches.

---

## Routing Domains

Domains are high-level categories that group related instructions. Each instruction file belongs to one or more domains.

| Domain | Description | Example Instructions |
|--------|-------------|---------------------|
| `software_engineering` | Development practices, code quality | python_script_development, git_safety |
| `project_management` | PM methodology, work tracking | time_free_project_management, work_logging |
| `agentic_workflows` | Agent behavior, decision making | agentic_decision_making, agent_compliance_framework |
| `architecture` | System design, organization | repository_organization |
| `quality` | Code review, environments | pull_request_workflow, environment_configuration |
| `safety_prevention` | Error prevention, validation | validation_first_execution, systematic_prevention_framework |
| `testing` | Test patterns, observability | observability_testing |
| `validation` | Verification, determinism | verification_efficiency, deterministic_validation_framework |
| `devops` | Logging, monitoring | audit_logging_patterns, observability_patterns |
| `development` | Token usage, context | token_usage_context_management |
| `github_integration` | GitHub API, projects | github_essentials, github_sub_issues |
| `trust_execution` | Trust-based workflows | trust_based_task_execution, feature_development |

---

## Priority Levels

Instructions are prioritized during routing conflicts:

| Priority | Meaning | When to Use |
|----------|---------|-------------|
| `P0` | Critical, always relevant | Safety, compliance, core workflows |
| `P1` | Standard importance | Most operational guidance |
| `P2` | Contextual importance | Specialized or optional guidance |

---

## Tag Formatting Standard

**Rule**: Use underscores (`_`) for multi-word tags. Never use spaces.

**Rationale**: Spaces in tags cause word collision false-positives during routing. For example, `project management` could match any message containing "project" or "management" individually.

| Incorrect | Correct |
|-----------|---------|
| `project management` | `project_management` |
| `git safety` | `git_safety` |
| `multi pass analysis` | `multi_pass_analysis` |
| `pull request` | `pull_request` |

**Alternatives**:
- Underscores: `project_management` (preferred)
- Dots: `project.management` (acceptable)
- CamelCase: `projectManagement` (avoid - harder to read)

---

## Keyword Patterns

The routing engine matches user messages against instruction keywords. Common patterns:

### Action Keywords
- `create`, `add`, `implement` → Development instructions
- `fix`, `debug`, `troubleshoot` → Safety/validation instructions
- `commit`, `push`, `branch` → Git/software_engineering instructions
- `test`, `validate`, `verify` → Testing/validation instructions

### Context Keywords
- `github`, `issue`, `pr`, `pull request` → github_integration
- `wiki`, `docs`, `documentation` → documentation domains
- `deploy`, `release`, `ship` → devops/deployment
- `log`, `track`, `record` → project_management/logging

---

## Frontmatter Schema

Each instruction file declares its routing metadata:

```yaml
---
title: "Instruction Title"
domains:
  - primary_domain
  - secondary_domain
priority: P1
keywords:
  - specific_keyword
  - another_keyword
triggers:
  - "pattern to match"
---
```

### Required Fields

- `title`: Human-readable instruction name
- `domains`: List of routing domains (at least one)
- `priority`: P0, P1, or P2

### Optional Fields

- `keywords`: Specific terms to match
- `triggers`: Phrase patterns that activate this instruction

---

## Routing Engine Versions

Pongogo uses versioned routing engines:

| Version | Status | Features |
|---------|--------|----------|
| `durian-0.0` | Deprecated | Basic keyword matching |
| `durian-0.5` | Deprecated | Domain taxonomy, priority weighting |
| `durian-0.6` | Stable | 12 IMP features, bundle boosts, semantic flags |
| `durian-0.6.1` | Current | Bug fixes, stability improvements |
| `durian-1.0` | Planned | Segment-aware routing |

The `compatibility.routing_engine_version` field in `manifest.yaml` specifies the minimum required version.

---

## Updating the Registry

When adding new domains or modifying routing behavior:

1. Update this registry document
2. Update `manifest.yaml` with new domain definitions
3. Update instruction files with new frontmatter
4. Run routing evaluation to verify accuracy

---

## Related Documentation

- `manifest.yaml` - Bundle manifest with category definitions
- `docs/design/seeded-instructions-analysis.md` - Instruction evaluation methodology
- Routing engine source: `src/mcp-server/routing_engine.py`
