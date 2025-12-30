# Seeded Instructions Guide

This document defines the rules for creating, scrubbing, and versioning seeded instruction files for pongogo-to-go.

## Classification System

Instruction files from the source repository are classified into four categories:

| Classification | Description | Action |
|----------------|-------------|--------|
| **ADOPT** | Generic best practices, no project-specific content | Copy with scrubbing pass |
| **ADAPT** | Valuable patterns requiring parameterization | Copy with scrubbing + placeholder substitution |
| **INSPIRE** | Complex files used as templates for simpler versions | Create new simplified version |
| **SKIP** | Project-specific, not portable | Do not include |

## Scrubbing Rules

All files (including ADOPT) require a scrubbing pass to remove project-specific references.

### REMOVE (from all files)

| Pattern | Example | Reason |
|---------|---------|--------|
| Internal project names | Howl, Springbound | Project-specific |
| Task/Issue references | Task #XXX, Issue #YYY | Internal tracking |
| PI references | PI-XXX | Internal improvement tracking |
| AD references | AD-XXX | Internal decision tracking |
| Absolute paths | `/Users/max/...`, `/tmp/...` | Machine-specific |
| Milestone references | P01, P02, P03 | Internal roadmap |
| Source attribution | `source: "Adapted from Howl"` | Internal provenance |
| RCA references | RCA-YYYY-MM-DD | Internal incident tracking |
| Specific evidence | `Evidence: Issue #143...` | Internal context |

### KEEP

| Pattern | Example | Reason |
|---------|---------|--------|
| "Pongogo" as tool name | "Pongogo routing system" | Product identity |
| Generic methodology | Time-free PM principles | Reusable patterns |
| Code examples | Python, bash snippets | Educational value |
| Validation checklists | Markdown checkboxes | Actionable guidance |

### REPLACE (ADAPT files only)

ADAPT files use placeholders that are resolved during `pongogo init`:

| Original | Placeholder | Resolved To |
|----------|-------------|-------------|
| `wiki/` | `{wiki_path}` | User's wiki location |
| `docs/` | `{docs_path}` | User's docs location |
| `pongogo/pongogo` | `{org}/{repo}` | User's GitHub org/repo |
| `knowledge/instructions/` | `{instructions_path}` | User's instruction path |
| Specific URLs | `https://github.com/{org}/{repo}/...` | User's repo URLs |

## Keyword Format Convention

**IMPORTANT**: Multi-word keywords use underscores, not spaces.

### Why Underscores?

The Pongogo routing engine tokenizes user queries into individual words. Space-separated keywords cause false positives:

```
Query: "free trial setup"
Tokenizes to: ["free", "trial", "setup"]

Problem with space-separated keywords:
- Keyword "time free" → "free" matches → FALSE POSITIVE!
- Keyword "free trial" → "free" matches → CORRECT

Solution with underscore keywords:
- Keyword "time_free" → "free" does NOT match → NO false positive
- Router generates n-grams: "free_trial" → EXACT MATCH
```

### Keyword Format Rules

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| `time free` | `time_free` |
| `work log entry` | `work_log_entry` |
| `no estimates` | `no_estimates` |
| `git commit` | `git_commit` |

### Example Frontmatter

```yaml
routing:
  priority: 1
  triggers:
    keywords:
      - time_free           # Multi-word: use underscores
      - no_estimates        # Multi-word: use underscores
      - complexity_based    # Multi-word: use underscores
      - planning            # Single word: no underscore needed
    nlp: "Time-free project management using complexity-based scoping"
```

### Router Behavior

The durian routing engine (0.6.1+):
1. Extracts individual words from query
2. Generates underscore-joined n-grams (2-grams, 3-grams)
3. Matches n-grams against underscore keywords EXACTLY
4. Single-word keywords still use substring matching

Example query processing:
```
Query: "how do I use time free project management"
Extracted: ["how", "use", "time", "free", "project", "management"]
Generated n-grams: ["time_free", "free_project", "project_management",
                    "time_free_project", "free_project_management"]
Matches: "time_free" keyword → EXACT MATCH (score +15)
```

## Versioning Format

### Two-Level Versioning

1. **Bundle Version** (in `manifest.yaml`)
   - SemVer format: `major.minor.patch`
   - Tracks the entire instruction set
   - Example: `bundle_version: "1.0.0"`

2. **File Version** (in each file's frontmatter)
   - SemVer format: `major.minor.patch`
   - Tracks individual file changes
   - Example: `version: "1.0.0"`

### Frontmatter Schema

```yaml
---
title: "Human-readable title"
description: "One-line description for routing"
version: "1.0.0"
last_updated: "2025-12-18T15:30:00-05:00"  # ISO 8601 with timezone
applies_to:
  - "glob/patterns/**/*.py"
domains:
  - "category_name"
priority: "P0|P1|P2"
patterns:
  - "pattern_tag"
routing:
  priority: 1
  triggers:
    keywords:
      - keyword_one      # Use underscores for multi-word
      - keyword_two
    nlp: "Natural language description for semantic matching"
---
```

### Timestamp Format

- **Format**: ISO 8601 with timezone offset
- **Example**: `2025-12-18T15:30:00-05:00`
- **Rationale**: Unambiguous, machine-parseable, timezone-aware

### Version Increment Rules

| Change Type | Version Bump | Example |
|-------------|--------------|--------|
| Typo fix, formatting | Patch | 1.0.0 → 1.0.1 |
| New section, expanded guidance | Minor | 1.0.0 → 1.1.0 |
| Restructure, breaking changes | Major | 1.0.0 → 2.0.0 |

## Manifest Structure

The `manifest.yaml` file tracks all seeded instructions:

```yaml
bundle_version: "1.0.0"
created_date: "2025-12-18"
description: "Seeded instruction files for Pongogo"

categories:
  category_name:
    description: "Category description"
    enabled_by_default: true
    files:
      - path: "category/file.instructions.md"
        version: "1.0.0"
        title: "File Title"
        domains: ["domain1", "domain2"]
        priority: "P1"

placeholders:
  "{placeholder}": "Description of what it resolves to"

compatibility:
  min_pongogo_version: "0.1.0"
  routing_engine_version: "durian-0.6.1+"  # Underscore keyword matching

stats:
  total_files: 5
  total_lines: ~2400
  categories: 2
```

## Update Flow (Future)

The update mechanism is designed but not yet implemented:

1. User runs `pongogo update --check`
2. System compares local `manifest.bundle_version` with remote
3. If newer version available, shows diff of changed files
4. User approves update
5. System downloads and replaces files (handling user modifications TBD)

## Adding New Seeded Instructions

1. **Classify** the source file (ADOPT/ADAPT/INSPIRE/SKIP)
2. **Scrub** according to rules above
3. **Format keywords** with underscores for multi-word terms
4. **Add versioning** frontmatter with `version` and `last_updated`
5. **Update manifest** with file entry
6. **Test routing** to ensure keywords trigger correctly
