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

## Pass 0: Dimension Discovery

### Goal
Sample files across categories to identify and validate the dimensions by which we should evaluate portability.

### Procedure

**Sample Selection** (10-15 files across different categories):

1. **Read each sample file COMPLETELY** - every line, every section
2. **Document observations**:
   - What external systems does this file assume? (GitHub, Docker, specific tools)
   - What concepts/methodologies does this assume? (Pongogo-specific, generic agile)
   - What terminology requires insider knowledge?
   - What file/folder structure does this assume?
   - Who is the intended audience? (AI agents, humans, both)
   - Are there other dependency types not captured above?

3. **Synthesize dimensions**:
   - Confirm or refine the proposed dimensions
   - Add any new dimensions discovered
   - Define scoring criteria for each dimension

### Proposed Dimensions (to validate)

| Dimension | What It Measures | Scoring Criteria |
|-----------|------------------|------------------|
| **System Dependencies** | External systems assumed | NONE / STANDARD (Git, GitHub) / SPECIFIC (Docker, MCP) / PONGOGO (routing, eval) |
| **Conceptual Dependencies** | Methodology/framework assumed | UNIVERSAL / INDUSTRY (agile, PM) / PONGOGO-METHOD |
| **Terminology Dependencies** | Jargon requiring translation | NONE / STANDARD / PONGOGO (PI, IMP, durian) |
| **Structural Dependencies** | File/folder assumptions | NONE / GENERIC / PONGOGO-SPECIFIC |
| **Audience Assumptions** | Who is this written for | UNIVERSAL / AGENT-PRIMARY / PONGOGO-AGENT |

### Sample Files to Read (one from each major category type)

1. `_foundational.instructions.md` (root - meta)
2. `agentic_workflows/multi_pass_iterative_analysis.instructions.md` (workflow)
3. `architecture/architecture_principles.instructions.md` (architecture)
4. `development_standards/commit_message_format.instructions.md` (standards)
5. `github_integration/github_project_status_workflow.instructions.md` (integration)
6. `learning/retrospective_triggers.instructions.md` (learning)
7. `project_management/time_free_project_management.instructions.md` (PM)
8. `safety_prevention/git_safety.instructions.md` (safety)
9. `routing/routing_engine_versioning.instructions.md` (routing - likely Pongogo-specific)
10. `evaluation/ground_truth_tagging_methodology.instructions.md` (eval - likely Pongogo-specific)
11. `documentation/documentation_placement.instructions.md` (docs)
12. `validation/validation_essentials.instructions.md` (validation)

### Output
- Validated/refined dimension framework
- Scoring criteria for each dimension
- Any new dimensions discovered
- Updated procedure for Pass 1-3

### Completion Criteria
- [ ] All 12 sample files read completely
- [ ] Each dimension validated or refined
- [ ] Scoring criteria defined
- [ ] User review of dimension framework before Pass 1

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
Read every file again to score each dimension discovered in Pass 0.

### Procedure

**For each of the 108 files:**

1. **Read the ENTIRE file again** - fresh eyes, dimension-focused

2. **Score each dimension**:

   **System Dependencies** (what external systems are assumed?):
   - `NONE`: No external system dependencies
   - `STANDARD`: Only Git/GitHub (widely used)
   - `SPECIFIC`: Docker, MCP, Claude Code, specific tools
   - `PONGOGO`: Routing engine, eval system, PI system

   **Conceptual Dependencies** (what methodology is assumed?):
   - `UNIVERSAL`: Applies to any software project
   - `INDUSTRY`: Standard industry concepts (agile, PM, etc.)
   - `PONGOGO-METHOD`: Pongogo-specific methodology/approach

   **Terminology Dependencies** (what jargon is used?):
   - `NONE`: Plain language throughout
   - `STANDARD`: Industry-standard terms (PR, CI/CD, etc.)
   - `PONGOGO`: Internal terms (PI, IMP, durian, etc.)

   **Structural Dependencies** (what file/folder structure assumed?):
   - `NONE`: Self-contained, no path references
   - `GENERIC`: References generic patterns (docs/, wiki/, etc.)
   - `PONGOGO-SPECIFIC`: References Pongogo paths/structure

   **Audience Assumptions** (who is this written for?):
   - `UNIVERSAL`: Any developer/team
   - `AGENT-PRIMARY`: Assumes AI agent reader but applicable
   - `PONGOGO-AGENT`: Specific to Pongogo's agent system

3. **Count specific references**:
   - Pongogo name references
   - PI- references
   - IMP- references
   - durian references
   - Pongogo-specific file paths
   - Total count

4. **List jargon requiring translation**:
   - Each internal term that would need explanation/replacement

5. **Record in Pass 2 table**

### Output Format

```markdown
### `filename.instructions.md`

| Dimension | Score | Evidence |
|-----------|-------|----------|
| System Dependencies | STANDARD | References GitHub, Git |
| Conceptual Dependencies | UNIVERSAL | Generic project management |
| Terminology Dependencies | PONGOGO | Uses "PI" 5x, "IMP" 2x |
| Structural Dependencies | PONGOGO-SPECIFIC | References knowledge/instructions/ |
| Audience Assumptions | AGENT-PRIMARY | "When Claude Code..." |

**Reference Counts**: Pongogo: 3, PI-: 5, IMP-: 2, durian: 0, paths: 4, **Total: 14**

**Jargon to Translate**: PI→improvement, IMP→implementation, specific paths→generic
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

2. **Apply classification matrix**:

   **Ship As-Is** (portable immediately):
   - System: NONE or STANDARD
   - Conceptual: UNIVERSAL or INDUSTRY
   - Terminology: NONE or STANDARD
   - Structural: NONE or GENERIC
   - Audience: UNIVERSAL or AGENT-PRIMARY
   - Reference count: ≤ 2

   **System-Specific Ship** (portable to users of that system):
   - System: SPECIFIC (e.g., GitHub-specific, Docker-specific)
   - Content valuable for users of that system
   - May need minor terminology cleanup

   **Needs Abstraction** (valuable but requires work):
   - Any dimension at PONGOGO level but core concept is universal
   - Reference count: 3+
   - Terminology needs translation

   **Don't Ship** (Pongogo-internal only):
   - Multiple dimensions at PONGOGO level
   - Core concept is Pongogo-specific
   - No value without Pongogo infrastructure

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
   - Specific terminology changes
   - Sections to remove or generalize
   - Structural changes needed
   - Estimated effort: SMALL (< 30 min) / MEDIUM (30-60 min) / LARGE (> 60 min)

5. **Record in Pass 3 table**

### Output Format

```markdown
### `filename.instructions.md`

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

### After Pass 0 (Dimension Discovery)
- [ ] All sample files (12) read completely
- [ ] Dimension framework validated/refined
- [ ] Scoring criteria clear and usable
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
