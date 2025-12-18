# Seeded Instructions Analysis Procedure

**Purpose**: Step-by-step procedure for analyzing Super Pongogo instruction files to determine what ships with pongogo-to-go.

**Related**: `seeded-instructions-analysis.md` (tracking document)

**Philosophy**: Thoroughness prevents rework. Every pass reads every line of every file. Partial reads lead to missed dependencies and incorrect classifications.

---

## Overview

This multi-pass analysis examines 108 instruction files across 26 folders to determine:
1. What portability dimensions exist across the instruction corpus
2. What content is universally applicable to any engineering project
3. What content is system-specific but broadly useful (e.g., GitHub-specific)
4. What content is Pongogo-specific and should not ship
5. What content needs abstraction to become portable

---

## Pass 0: Dimension Discovery ✅ COMPLETE

### Goal
Sample files across categories to identify and validate the dimensions by which we should evaluate portability.

### Sample Files Read (12 files, ~5,000 lines total)

1. `_foundational.instructions.md` (91 lines) - Root meta file
2. `multi_pass_iterative_analysis.instructions.md` (400 lines) - Analysis methodology
3. `architecture_principles.instructions.md` (180 lines) - Core principles
4. `commit_message_format.instructions.md` (808 lines) - Git standards
5. `github_project_status_workflow.instructions.md` (470 lines) - GitHub integration
6. `retrospective_triggers.instructions.md` (986 lines) - Learning loops
7. `time_free_project_management.instructions.md` (413 lines) - PM philosophy
8. `git_safety.instructions.md` (381 lines) - Safety protocols
9. `routing_engine_versioning.instructions.md` (393 lines) - Internal infrastructure
10. `ground_truth_tagging_methodology.instructions.md` (376 lines) - Eval methodology
11. `documentation_placement.instructions.md` (349 lines) - Doc structure
12. `validation_essentials.instructions.md` (360 lines) - Quality standards

### Validated Dimensions (5 dimensions confirmed)

All proposed dimensions validated with evidence from sample files:

| Dimension | What It Measures | Validated Evidence |
|-----------|------------------|-------------------|
| **System Dependencies** | External systems assumed | Clear gradation: NONE → STANDARD (Git) → SPECIFIC (Docker, MCP) → PONGOGO (routing, eval) |
| **Conceptual Dependencies** | Methodology/framework assumed | Distinct levels: UNIVERSAL (any project) → INDUSTRY (agile) → PONGOGO-METHOD (10 principles) |
| **Terminology Dependencies** | Jargon requiring translation | Clear internal terms: PI, IMP, durian, Pongogo-specific paths |
| **Structural Dependencies** | File/folder assumptions | Range from self-contained to Pongogo-specific paths |
| **Audience Assumptions** | Who is this written for | From UNIVERSAL to PONGOGO-AGENT specific |

### Refined Scoring Criteria

**System Dependencies** (numeric for aggregation):
| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 0 | `NONE` | No external system required | Self-contained concepts |
| 1 | `STANDARD` | Git, GitHub, common tools | Widely used, industry standard |
| 2 | `PLATFORM-SPECIFIC` | Docker, MCP, Claude Code | Specific platforms/tools |
| 3 | `PONGOGO-INTERNAL` | Routing engine, eval system, PI system | Pongogo infrastructure |

**Conceptual Dependencies**:
| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 0 | `UNIVERSAL` | Applies to any software project | Git safety, commit format |
| 1 | `INDUSTRY` | Standard agile/PM/engineering | Retrospectives, validation |
| 2 | `PONGOGO-METHOD` | Pongogo's specific methodology | 10 principles, time-free PM |

**Terminology Dependencies**:
| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 0 | `PLAIN` | No jargon, plain language | Simple English |
| 1 | `INDUSTRY` | Standard terms (PR, CI/CD, agile) | Industry vocabulary |
| 2 | `PONGOGO-JARGON` | Internal terms (PI, IMP, durian) | Needs translation |

**Structural Dependencies**:
| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 0 | `SELF-CONTAINED` | No path references | Standalone content |
| 1 | `GENERIC-PATTERNS` | Generic docs/, wiki/, instructions/ | Transferable structure |
| 2 | `PONGOGO-PATHS` | Specific Pongogo paths | `pongogo-knowledge-server/`, `knowledge/instructions/pongogo/` |

**Audience Assumptions**:
| Score | Level | Description | Examples |
|-------|-------|-------------|----------|
| 0 | `UNIVERSAL` | Any developer/team | General guidance |
| 1 | `AGENT-AWARE` | Assumes AI agent but broadly applicable | Agent patterns |
| 2 | `PONGOGO-AGENT` | Specific to Pongogo's agent config | Pongogo-specific agents |

### Sample File Quick Classification (Preview)

Based on Pass 0 reading, preliminary classification:

| File | Likely Decision | Key Observation |
|------|-----------------|-----------------|
| `_foundational.instructions.md` | Don't Ship | Meta file for Pongogo context |
| `multi_pass_iterative_analysis.instructions.md` | Needs Abstraction | Universal methodology, has PI references |
| `architecture_principles.instructions.md` | Needs Abstraction | Good principles, heavy Pongogo branding |
| `commit_message_format.instructions.md` | Ship As-Is | Universal git practices |
| `github_project_status_workflow.instructions.md` | System-Specific (GitHub) | GitHub-specific but valuable |
| `retrospective_triggers.instructions.md` | Needs Abstraction | Universal learning, Pongogo terminology |
| `time_free_project_management.instructions.md` | Ship As-Is / Minor Abstraction | Universal PM philosophy |
| `git_safety.instructions.md` | Ship As-Is | Universal git safety |
| `routing_engine_versioning.instructions.md` | Don't Ship | Pongogo internal infrastructure |
| `ground_truth_tagging_methodology.instructions.md` | Needs Abstraction | Universal methodology, Pongogo references |
| `documentation_placement.instructions.md` | Needs Abstraction | Universal patterns, Pongogo paths |
| `validation_essentials.instructions.md` | Needs Abstraction | Universal validation, Pongogo references |

### Pass 0 Completion Criteria ✅

- [x] All 12 sample files read completely (~5,000 lines total)
- [x] Each dimension validated with evidence
- [x] Scoring criteria defined with numeric values
- [x] Preliminary classification preview created
- [ ] **USER REVIEW** of dimension framework before Pass 1

---

## Pass 1: Inventory & Complete Overview

### Goal
Read every line of every file to create a comprehensive inventory with full understanding.

### Procedure

**For each of the 108 files:**

1. **Read the ENTIRE file** - every line, start to finish

2. **Extract comprehensive metadata**:
   - **Purpose Statement**: The file's stated purpose (usually in header)
   - **Keywords**: 5-7 key terms that capture the file's domain
   - **Sections**: List of major sections/headers in the file
   - **Key Concepts**: Main ideas, patterns, or frameworks taught
   - **Dependencies Noted**: What systems/files/concepts does it reference?
   - **Line Count**: Total lines
   - **Content Quality**: STRONG / ADEQUATE / WEAK (subjective assessment)

3. **Write 3-5 sentence overview**:
   - What problem does this instruction solve?
   - What guidance does it provide?
   - What would happen if an agent didn't have this instruction?

4. **Record in tracking document** under the folder's Pass 1 table

### Output Format

```markdown
### `filename.instructions.md` (XXX lines)

**Purpose**: [Exact purpose statement from file]

**Keywords**: keyword1, keyword2, keyword3, keyword4, keyword5

**Sections**: 
- Section 1
- Section 2
- ...

**Key Concepts**: [Main ideas/patterns]

**Dependencies Noted**: [Systems, files, concepts referenced]

**Overview**: [3-5 sentence summary answering: what problem, what guidance, why needed]

**Content Quality**: STRONG / ADEQUATE / WEAK
```

### Processing Order

Process folders alphabetically:
1. Root files (3 files)
2. `agentic_workflows/` (4 files)
3. `architecture/` (4 files)
4. `compliance/` (1 file)
5. `data_management/` (1 file)
6. `development/` (1 file)
7. `development_standards/` (8 files)
8. `devops/` (6 files)
9. `documentation/` (7 files)
10. `evaluation/` (6 files)
11. `github/` (4 files)
12. `github_integration/` (4 files)
13. `infrastructure/` (2 files)
14. `learning/` (10 files)
15. `mcp/` (2 files)
16. `process/` (3 files)
17. `project_management/` (14 files)
18. `quality/` (4 files)
19. `research/` (2 files)
20. `routing/` (4 files)
21. `safety_prevention/` (3 files)
22. `scripting/` (2 files)
23. `security/` (1 file)
24. `testing/` (1 file)
25. `trust_execution/` (3 files)
26. `validation/` (4 files)

### Completion Criteria
- [ ] All 108 files read completely
- [ ] Each file has full metadata captured
- [ ] No shortcuts taken (no partial reads)
- [ ] User review of Pass 1 data before Pass 2

---

## Pass 2: Multi-Dimensional Portability Scoring

### Goal
Read every file again to score each dimension validated in Pass 0.

### Procedure

**For each of the 108 files:**

1. **Read the ENTIRE file again** - fresh eyes, dimension-focused

2. **Score each dimension** (using validated scoring from Pass 0):

   **System Dependencies** (0-3):
   - `0 NONE`: No external system dependencies
   - `1 STANDARD`: Only Git/GitHub (widely used)
   - `2 PLATFORM-SPECIFIC`: Docker, MCP, Claude Code, specific tools
   - `3 PONGOGO-INTERNAL`: Routing engine, eval system, PI system

   **Conceptual Dependencies** (0-2):
   - `0 UNIVERSAL`: Applies to any software project
   - `1 INDUSTRY`: Standard industry concepts (agile, PM, etc.)
   - `2 PONGOGO-METHOD`: Pongogo-specific methodology/approach

   **Terminology Dependencies** (0-2):
   - `0 PLAIN`: Plain language throughout
   - `1 INDUSTRY`: Industry-standard terms (PR, CI/CD, etc.)
   - `2 PONGOGO-JARGON`: Internal terms (PI, IMP, durian, etc.)

   **Structural Dependencies** (0-2):
   - `0 SELF-CONTAINED`: Self-contained, no path references
   - `1 GENERIC-PATTERNS`: References generic patterns (docs/, wiki/, etc.)
   - `2 PONGOGO-PATHS`: References Pongogo-specific paths/structure

   **Audience Assumptions** (0-2):
   - `0 UNIVERSAL`: Any developer/team
   - `1 AGENT-AWARE`: Assumes AI agent reader but applicable
   - `2 PONGOGO-AGENT`: Specific to Pongogo's agent system

3. **Count specific references**:
   - Pongogo name references (count)
   - PI- references (count)
   - IMP- references (count)
   - durian references (count)
   - Pongogo-specific file paths (count)
   - **Total internal references** (sum)

4. **List jargon requiring translation**:
   - Each internal term that would need explanation/replacement
   - Suggested generic replacement

5. **Record in Pass 2 table**

### Output Format

```markdown
### `filename.instructions.md`

| Dimension | Score | Level | Evidence |
|-----------|-------|-------|----------|
| System Dependencies | 1 | STANDARD | References GitHub, Git |
| Conceptual Dependencies | 0 | UNIVERSAL | Generic project management |
| Terminology Dependencies | 2 | PONGOGO-JARGON | Uses "PI" 5x, "IMP" 2x |
| Structural Dependencies | 2 | PONGOGO-PATHS | References knowledge/instructions/ |
| Audience Assumptions | 1 | AGENT-AWARE | "When Claude Code..." |

**Portability Score**: 6/11 (lower = more portable)

**Reference Counts**: Pongogo: 3, PI-: 5, IMP-: 2, durian: 0, paths: 4, **Total: 14**

**Jargon to Translate**: 
- PI → improvement pattern
- IMP → implementation
- knowledge/instructions/ → {project}/instructions/
```

### Completion Criteria
- [ ] All 108 files scored on all dimensions
- [ ] Evidence documented for each score
- [ ] Reference counts tallied
- [ ] Jargon lists complete
- [ ] User review of Pass 2 data before Pass 3

---

## Pass 3: Classification Decision

### Goal
Synthesize dimension scores into final shipping decisions for each file.

### Procedure

**For each of the 108 files:**

1. **Review all Pass 1 and Pass 2 data** for the file

2. **Apply classification matrix** (based on dimension scores):

   **Ship As-Is** (portable immediately):
   - Portability Score: ≤ 3 (all dimensions low)
   - System: 0-1 (NONE or STANDARD)
   - Conceptual: 0-1 (UNIVERSAL or INDUSTRY)
   - Terminology: 0-1 (PLAIN or INDUSTRY)
   - Structural: 0-1 (SELF-CONTAINED or GENERIC)
   - Audience: 0-1 (UNIVERSAL or AGENT-AWARE)
   - Total internal references: ≤ 2

   **System-Specific Ship** (portable to users of that system):
   - System: 2 (PLATFORM-SPECIFIC like GitHub, Docker)
   - Other dimensions: 0-1
   - Content valuable for users of that system
   - May need minor terminology cleanup

   **Needs Abstraction** (valuable but requires work):
   - Any dimension at level 2 (PONGOGO/JARGON/PATHS/AGENT)
   - But core concept is universal (Conceptual ≤ 1)
   - Total internal references: 3+
   - Terminology translation needed

   **Don't Ship** (Pongogo-internal only):
   - Multiple dimensions at level 2
   - System: 3 (PONGOGO-INTERNAL)
   - Conceptual: 2 (PONGOGO-METHOD with no universal value)
   - Core concept requires Pongogo infrastructure
   - No value without routing/eval/PI system

3. **Assign target category** (for files that ship):
   - `core/` - Fundamental system mechanics
   - `learning/` - Retros, work logging, improvement tracking
   - `project_management/` - Issue lifecycle, scope, glossary
   - `development/` - Commits, code review, testing, standards
   - `documentation/` - Docs structure, placement, wiki
   - `safety/` - Git safety, validation, prevention
   - `github/` - GitHub-specific workflows (system-specific)
   - `devops/` - CI/CD, containers, infrastructure
   - `agentic/` - Agent-specific patterns and compliance

4. **Document abstraction requirements** (if needed):
   - Specific terminology changes with counts
   - Sections to remove or generalize
   - Structural changes needed
   - Estimated effort: SMALL (< 30 min) / MEDIUM (30-60 min) / LARGE (> 60 min)

5. **Record in Pass 3 table**

### Output Format

```markdown
### `filename.instructions.md`

**Portability Score**: 6/11

**Decision**: Ship As-Is / System-Specific Ship / Needs Abstraction / Don't Ship

**Target Category**: `category/`

**Reasoning**: [Why this decision based on dimension scores]

**Abstraction Requirements** (if applicable):
- [ ] Replace "PI" with "improvement pattern" (12 instances)
- [ ] Generalize `/pongogo/` paths to `{project}/`
- [ ] Remove Section 4 (Pongogo-specific tooling)
- Estimated effort: MEDIUM
```

### Completion Criteria
- [ ] All 108 files classified
- [ ] Each decision has clear reasoning
- [ ] Target categories assigned for shipping files
- [ ] Abstraction requirements documented
- [ ] User approval of classifications before implementation

---

## Quality Gates

### After Pass 0 (Dimension Discovery) ✅ COMPLETE
- [x] All sample files (12) read completely
- [x] Dimension framework validated/refined
- [x] Scoring criteria clear and usable
- [ ] **USER REVIEW REQUIRED** before Pass 1

### After Pass 1 (Inventory & Overview)
- [ ] All 108 files read completely
- [ ] Full metadata captured for each file
- [ ] No partial reads or shortcuts
- [ ] **USER REVIEW REQUIRED** before Pass 2

### After Pass 2 (Dimension Scoring)
- [ ] All 108 files scored on all dimensions
- [ ] Evidence documented for each score
- [ ] Reference counts and jargon lists complete
- [ ] **USER REVIEW REQUIRED** before Pass 3

### After Pass 3 (Classification)
- [ ] All 108 files classified
- [ ] Decisions have clear reasoning
- [ ] Categories and abstraction requirements documented
- [ ] **USER APPROVAL REQUIRED** before implementation

---

## Implementation Phase (Post-Analysis)

After Pass 3 approval, implementation work includes:

1. **Ship As-Is files**: Copy to pongogo-to-go with minimal formatting cleanup
2. **System-Specific files**: Organize by system, minor terminology cleanup
3. **Needs Abstraction files**: Create portable versions per abstraction requirements
4. **Don't Ship files**: Document reasoning for future reference

This implementation work is tracked separately (Task #300 or equivalent).

---

## Notes

- **Thoroughness is non-negotiable**: Every line of every file in every pass
- **Fresh eyes each pass**: Reading with different focus each time reveals different things
- **User gates prevent wasted effort**: Review after each pass catches errors early
- **Evidence-based scoring**: Every score needs documented evidence
- **Track discoveries**: Update this procedure if new patterns emerge during analysis
