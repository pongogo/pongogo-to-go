# Seeded Instructions Analysis Procedure

**Purpose**: Step-by-step procedure for analyzing Super Pongogo instruction files to determine what ships with pongogo-to-go.

**Related**: `seeded-instructions-analysis.md` (tracking document)

---

## Overview

This multi-pass analysis examines 108 instruction files across 26 folders to determine:
1. What content is universally applicable to any engineering project
2. What content is Pongogo-specific and should not ship
3. What content needs abstraction to become portable

---

## Pass 1: Inventory & Overview

### Goal
Create a complete inventory of all instruction files with basic metadata.

### Procedure

**For each folder:**

1. **Read each file** in the folder (first ~50 lines for overview)

2. **Extract metadata**:
   - **Keywords**: 3-5 key terms from filename and content purpose
   - **Overview**: 1-2 sentence summary of what the instruction does
   - **Lines**: Total line count

3. **Record in tracking document** under the folder's table

### Output Format

```markdown
| File | Keywords | Overview | Lines |
|------|----------|----------|-------|
| `filename.instructions.md` | keyword1, keyword2, keyword3 | One sentence summary of purpose. | 150 |
```

### Folder Processing Order

1. Root files (3)
2. agentic_workflows (4)
3. architecture (4)
4. ... (continue alphabetically)

### Completion Criteria
- All 108 files have Keywords, Overview, and Lines filled in
- No empty cells in Pass 1 tables

---

## Pass 2: Portability Assessment

### Goal
Assess each file's portability to external projects.

### Procedure

**For each file from Pass 1:**

1. **Count Pongogo-specific references**:
   - Search for: "Pongogo", "Super Pongogo", "pongogo-to-go"
   - Search for: "PI-", "IMP-", "durian"
   - Search for: File paths containing "/pongogo/"
   - Record total count

2. **Assess generic applicability**:
   - **HIGH**: Content applies to any engineering project as-is
   - **MEDIUM**: Content applies with minor terminology changes
   - **LOW**: Content is specific to Pongogo's architecture/methodology

3. **Identify jargon to remove**:
   - "PI" → "improvement" or "pattern"
   - "IMP" → remove version references
   - "durian" → "routing engine" (if shipping routing)
   - Pongogo-specific file paths → generic examples

4. **Record in Pass 2 table**

### Output Format

```markdown
| File | Pongogo Refs | Applicability | Jargon to Remove |
|------|--------------|---------------|------------------|
| `filename.instructions.md` | 5 | MEDIUM | PI→improvement, specific paths |
```

### Assessment Guidelines

**HIGH applicability indicators**:
- Generic software engineering practices
- Universal patterns (git, commits, PRs, testing)
- Process patterns that work for any team

**MEDIUM applicability indicators**:
- Good patterns with Pongogo-specific terminology
- References to Pongogo structure that could be generalized
- Methodology that's valuable but needs abstraction

**LOW applicability indicators**:
- References specific Pongogo infrastructure (routing engine, eval system)
- Depends on Pongogo-specific tooling
- Internal process only relevant to Pongogo development

### Completion Criteria
- All 108 files assessed for portability
- Each file has Pongogo Refs count, Applicability rating, and Jargon notes

---

## Pass 3: Classification Decision

### Goal
Make final decision on each file: ship, abstract, or don't ship.

### Procedure

**For each file from Pass 2:**

1. **Apply decision matrix**:

   | Applicability | Pongogo Refs | Decision |
   |---------------|--------------|----------|
   | HIGH | 0-2 | Ship as-is |
   | HIGH | 3+ | Needs abstraction |
   | MEDIUM | any | Needs abstraction |
   | LOW | any | Don't ship |

2. **Assign target category** (for files that ship):
   - `_pongogo_core/` - System mechanics (non-toggleable)
   - `learning/` - Retros, work logging, improvement tracking
   - `project_management/` - Issue lifecycle, scope, glossary
   - `development/` - Commits, code review, testing
   - `documentation/` - Three-tier docs, placement
   - `safety/` - Git safety, validation
   - (Other categories as patterns emerge)

3. **Document abstraction notes** (for files needing abstraction):
   - What terminology needs changing
   - What sections need removal or generalization
   - Estimated effort (small/medium/large)

4. **Record in Pass 3 table**

### Output Format

```markdown
| File | Decision | Target Category | Abstraction Notes |
|------|----------|-----------------|-------------------|
| `filename.instructions.md` | Needs abstraction | learning/ | Remove PI references, generalize paths |
```

### Decision Guidelines

**Ship as-is**: Universal content with minimal/no Pongogo references

**Needs abstraction**: Valuable content that requires:
- Terminology changes (PI→improvement)
- Path generalization
- Pongogo-specific example removal
- Section trimming

**Don't ship**: Content that is:
- Specific to Pongogo internal infrastructure
- Routing engine implementation details
- Eval system specifics
- Super Pongogo development processes

### Completion Criteria
- All 108 files have Decision, Target Category (if shipping), and Abstraction Notes (if needed)
- Clear mapping of files to seeded categories

---

## Pass 4: Abstraction & Writing

### Goal
Create portable versions of files marked "Needs abstraction"

### Procedure

**For each file marked "Needs abstraction":**

1. **Create new file** in target location:
   - `pongogo-to-go/instructions/{category}/{filename}.md`

2. **Apply abstraction**:
   - Replace Pongogo terminology with generic terms
   - Remove internal references and file paths
   - Generalize examples
   - Simplify structure if over-engineered for Pongogo's needs

3. **Preserve core value**:
   - Keep the underlying principle/pattern
   - Maintain practical applicability
   - Ensure standalone comprehensibility

4. **Review for user-friendliness**:
   - No unexplained jargon
   - Clear "when to apply" scenarios
   - Actionable guidance

### Output
- Portable instruction files in `pongogo-to-go/instructions/`
- Updated tracking document with completion status

### Completion Criteria
- All "Needs abstraction" files have portable versions
- No remaining Pongogo-specific terminology in shipped files
- Files are comprehensible to external users

---

## Quality Gates

### After Pass 1
- [ ] All 108 files inventoried
- [ ] No empty cells in tables
- [ ] Ready for user review before Pass 2

### After Pass 2
- [ ] All files assessed for portability
- [ ] Preliminary categorization visible
- [ ] Ready for user review before Pass 3

### After Pass 3
- [ ] Clear ship/don't ship decisions for all files
- [ ] Category assignments complete
- [ ] Ready for user approval before Pass 4

### After Pass 4
- [ ] All portable files created
- [ ] Seeded instruction sets complete
- [ ] User acceptance test passed

---

## Notes

- Each pass builds on the previous - don't skip passes
- User review/approval after each pass prevents wasted effort
- Track discoveries and decisions in the main analysis document
- Update this procedure if new dimensions emerge during analysis
