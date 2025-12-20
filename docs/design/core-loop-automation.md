# Core Loop Automation Design

**Spike**: #295 (core_loop_automation)
**Date**: 2025-12-19
**Status**: Draft

## Overview

This document defines which automation from Super Pongogo (internal) should be extracted for external users in pongogo-to-go, and how that extraction works.

---

## Adaptive Preference System

**Key Design Decision**: All triggers support three modes learned organically through use.

### Behavior Modes

| Mode | Behavior | User Experience |
|------|----------|-----------------|
| `auto` | Just do it | "Created work log entry for Task X" |
| `ask` | Prompt first | "Want me to create a work log entry?" |
| `skip` | Don't mention | Silent (user manages manually) |

### Learning Flow

**First occurrence of any trigger**:
1. Trigger detected (e.g., task completion)
2. Claude prompts: "I noticed you completed this task. Want me to create a work log entry?"
3. User responds (yes/no)
4. Claude asks: "Should I do this automatically for future completions, or always ask first?"
5. Preference saved to config

**Subsequent occurrences**:
- Behavior follows saved preference
- User can always override via `/pongogo-config`

### Configuration File

`.pongogo/preferences.yaml`:
```yaml
# Auto-generated through use - edit via /pongogo-config
version: 1
behaviors:
  work_log_on_completion:
    mode: auto  # auto | ask | skip
    learned_at: 2025-12-19

  retro_on_epic_completion:
    mode: ask
    learned_at: 2025-12-19

  github_issue_management:
    mode: skip  # user manages manually
    learned_at: 2025-12-19

  pi_threshold_prompt:
    mode: auto
    learned_at: 2025-12-19
```

### Foundational Instruction

`_pongogo_collaboration.instructions.md`:
- Included via frontmatter on trigger-based instructions
- Reads `.pongogo/preferences.yaml` at session start
- Provides helper patterns for preference-aware behavior
- Defines the "learn preference" interaction template

```markdown
## Preference-Aware Behavior Pattern

When executing a trigger-based action:

1. Check preferences for this behavior
2. If no preference exists:
   - Execute with prompt
   - Ask about future preference
   - Save to preferences.yaml
3. If preference exists:
   - auto: Execute silently, inform after
   - ask: Prompt before executing
   - skip: Do not execute or mention
```

### Routing Implications

The routing engine does NOT need changes for this system:
- Routing still routes to the same instructions
- Instructions check preferences and adjust behavior
- Preferences are instruction-level logic, not routing-level

However, the foundational instruction needs reliable inclusion:
- `_pongogo_collaboration.instructions.md` should route with high confidence on ALL queries
- May need frontmatter includes or always-on category

### Communication Bundling

When multiple `auto` actions occur together, bundle the communication:

**Bad** (noisy):
> "Created work log entry."
> "Captured decision in archive."
> "Noted strategic insight."

**Good** (bundled):
> "I've captured this session: work log entry created, decision archived, and strategic insight noted."

**Implementation**: Spike #329 explores communication preference design including bundling.

---

## Aligned Trigger Table

Based on systematic review of Super Pongogo workflows (Spike #295), the following triggers are extracted for pongogo-to-go with assigned default modes.

### Work Completion Triggers

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 1 | Task completion | Work finished | Prompt for work log | `ask` | Work log bundled with retro if user says YES |
| 2 | Epic completion | Epic closed | Prompt for L2 retro | `ask` | Includes work log |
| 3 | Milestone completion | Milestone closed | Prompt for L3 retro | `ask` | Includes summary |
| 4 | Session end | User exits | Session summary | `skip` | User manages manually |

### Learning Capture Triggers

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 5 | L1 Retro | Work complete | 4-question work log | `ask` | Work log bundled if YES |
| 6 | L2 Retro | Pattern detected | Work log + PI entries | `ask` | |
| 7 | L3 Retro | Systemic failure/success | RCA + PIs + instructions | `ask` | |
| 8 | RCA triggered | Incident/failure | Create RCA document | `ask` | `/pongogo-rca` command |
| 9 | RCA complete | RCA documented | Track follow-up actions | `auto` | Low risk, helpful |

### PI (Potential Improvement) Triggers

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 10 | Pattern noticed (1st) | Issue observed | Start tracking silently | `auto` | Low risk, demonstrates value |
| 11 | Same issue (2nd) | Recurrence | Increment count | `auto` | Silent tracking |
| 12 | Threshold crossed (3rd) | Pattern confirmed | Suggest instruction creation | `ask` | Key value moment |

### Knowledge Institutionalization Triggers

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 16 | Approach validated | User confirms approach | "I'll remember this for next time" | `ask` | Friendly commitment language |
| 17 | Decision made | Architectural choice | Capture in decision archive | `auto` | "Got it - I'll remember why we chose this" |
| 18 | Strategic insight | Domain learning | Note for future reference | `auto` | "That's useful - I've noted it" |
| 19 | Term used (3+) | Undefined term repeated | Suggest glossary candidate | `ask` | Threshold pattern like PIs |
| 20 | FAQ-worthy Q&A (3+) | Same question repeated | Suggest FAQ candidate | `ask` | Threshold pattern like PIs |

### Issue Lifecycle Triggers (GitHub PM Conditional)

**Prerequisite**: These triggers only activate if GitHub PM is detected during `pongogo init`. See Spike #331.

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 25 | Issue created | New task/epic | Apply template to body | `ask` | |
| 26 | Status → In Progress | Work starts | Verify prerequisites, update board | `ask` | |
| 27 | Status → Ready for Review | Work complete | Completion comment | `ask` | |
| 28 | Status → Done | Approved + closed | Final closure | `ask` | |
| 29 | Prerequisite complete | Blocker resolved | Notify blocked issue | `ask` | |

### Quality/Compliance Triggers (GitHub PM Conditional)

| # | Trigger | Event | Action | Default | Notes |
|---|---------|-------|--------|---------|-------|
| 31 | PR created | Branch ready | Apply PR template | `ask` | |
| 32 | PR merged | Code integrated | Changelog entry | `ask` | |

### Removed from Trigger Table

| Original # | Trigger | Reason |
|------------|---------|--------|
| 13-15 | PI status updates | Internal bookkeeping, not user-facing |
| 21 | Instruction created | Redundant with threshold trigger |
| 22-23 | Weekly/monthly summaries | `skip` default - user manages manually |
| 24 | Project status request | Not a trigger - user-initiated command (`/pongogo-recent-progress`) |
| 30 | Pre-commit hooks | Git-level, not Pongogo automation |
| 33 | Compliance check | Foundational pattern, not user-facing trigger |

### Slash Commands

User-initiated commands (not triggers):

| Command | Purpose |
|---------|---------|
| `/pongogo-retro` | Conduct learning loop on demand |
| `/pongogo-log` | Create work log entry on demand |
| `/pongogo-done` | Run completion checklist on demand |
| `/pongogo-rca` | Start RCA wizard on demand |
| `/pongogo-status` | MCP server status (enabled/disabled/simulate) |
| `/pongogo-recent-progress` | On-demand project accomplishment summary |
| `/pongogo-config` | Edit preferences |

---

## Existing Automation in Super Pongogo

The following automation runs today in Super Pongogo development:

| Automation | Trigger | What Happens |
|------------|---------|--------------|
| Work Log Entry | Task/Epic completion | Creates structured entry in monthly work log |
| Learning Loop | Milestone/Epic/Task completion | Conducts retrospective, captures learnings |
| RCA | Incident detection | Root cause analysis with corrective actions |
| PI Creation | Pattern observed 3x | Creates Potential Improvement entry |
| Issue Commencement | Task starts | Verifies prerequisites, updates status, creates context |
| Issue Closure | Task completes | Validates completion criteria, updates board |
| Strategic Checkpoint | Major milestone | Reviews progress, adjusts strategy |

### How It Works Today

These automations are **instruction-driven**. The MCP server routes to instruction files that tell Claude what to do:

```
User message → route_instructions() → relevant .instructions.md files → Claude follows them
```

For example, when I complete a task:
1. `retrospective_triggers.instructions.md` routes and tells me to conduct a learning loop
2. `work_logging.instructions.md` routes and tells me to create a work log entry
3. `issue_closure.instructions.md` routes and tells me the closure checklist

The automation isn't code - it's **knowledge routing + agent compliance**.

## Extraction for External Users

### Tier 1: Core (Ships in v1)

These are fundamental to the Pongogo value proposition:

| Automation | External User Benefit | Instructions Needed |
|------------|----------------------|---------------------|
| Learning Loop | Capture knowledge from completed work | `learning_loop_basic.instructions.md` |
| Work Logging | Track what was accomplished | `work_logging_basic.instructions.md` |
| Issue Closure | Consistent completion verification | `issue_closure_basic.instructions.md` |

### Tier 2: Enhanced (Ships in v1.1+)

Valuable but requires more context or complexity:

| Automation | Why Deferred |
|------------|--------------|
| RCA | Requires incident detection, more sophisticated |
| PI System | Requires database, pattern tracking |
| Strategic Checkpoint | Requires milestone structure |
| Issue Commencement | Requires GitHub integration depth |

### Tier 3: Advanced (Future)

Full Super Pongogo capability:

| Automation | Why Future |
|------------|------------|
| Full PI lifecycle | Database + observability |
| Multi-agent coordination | Architecture maturity |
| Segment-aware routing | durian-1.0 dependency |

## Packaging Strategy

### What Gets Extracted

For each Tier 1 automation, we create a **simplified instruction file** in `pongogo-to-go/instructions/_pongogo_core/`:

```
instructions/
  _pongogo_core/           # Always active
    learning_loop.instructions.md
    work_logging.instructions.md
    issue_closure.instructions.md
    routing_basics.instructions.md
```

### Simplification Principles

1. **Remove internal references**: No Super Pongogo wiki, no internal tools
2. **Remove GitHub-specific depth**: Basic integration, not full MCP tooling
3. **Self-contained**: Each instruction works standalone
4. **Progressive disclosure**: Simple default, optional advanced usage

### Example: Learning Loop (Simplified)

**Super Pongogo version** (`learning_loop_execution.instructions.md`):
- References wiki pages
- Requires specific retrospective format
- Integrates with PI system
- Links to strategic checkpoints

**pongogo-to-go version** (`learning_loop.instructions.md`):
- Simple 3-question retrospective
- Optional work log format
- No database dependencies
- Works with any project structure

## Trigger Mechanisms

### How Triggers Work in Super Pongogo

Triggers are NOT code hooks - they're **routing conditions**. When a user message matches certain patterns, relevant instructions route:

```python
# In routing engine (conceptual)
if message contains "done" or "completed" or "finished":
    route → learning_loop.instructions.md
    route → work_logging.instructions.md
```

### How Triggers Work in pongogo-to-go

Same pattern - the MCP server routes based on message content:

1. **Completion signals**: "done", "finished", "completed", "shipped"
2. **Problem signals**: "bug", "issue", "broken", "failed"
3. **Planning signals**: "plan", "design", "approach", "how should"

The routing engine already does this - we just need appropriate instruction files to route TO.

### Slash Commands as Explicit Triggers

For users who want explicit control:

```
/pongogo-retro      → Conduct learning loop
/pongogo-log        → Create work log entry
/pongogo-done       → Run completion checklist
```

These are **bundled in the pongogo-to-go package**, not separate.

## Implementation Architecture

```
pongogo-to-go/
├── src/
│   ├── cli/
│   │   └── main.py           # pongogo init
│   └── server/
│       ├── main.py           # MCP server entry
│       └── router.py         # Simplified routing
├── instructions/
│   ├── _pongogo_core/        # Always active (Tier 1)
│   ├── software_engineering/ # Optional category
│   └── project_management/   # Optional category
└── commands/                 # Slash commands
    ├── pongogo-retro.md
    ├── pongogo-log.md
    └── pongogo-done.md
```

## Success Criteria

### Tier 1 Complete When

1. User completes a task → Claude suggests learning loop (via routing)
2. User runs `/pongogo-retro` → Structured retrospective conducted
3. User runs `/pongogo-log` → Work log entry created
4. User runs `/pongogo-done` → Completion checklist verified

### Measurable

- 3 core instruction files ported and simplified
- 3 slash commands working
- Routing correctly triggers on completion signals
- Works without any Super Pongogo dependencies

## Implementation Tasks

Based on this design, the following tasks have been created:

| Issue | Title | Description |
|-------|-------|-------------|
| #332 | Foundational instruction | Create `_pongogo_collaboration.instructions.md` |
| #333 | Port core instructions | Extract and simplify Tier 1 instructions |
| #334 | Create slash commands | `/pongogo-retro`, `/pongogo-log`, `/pongogo-done`, etc. |
| #335 | Implement preferences.yaml | File-based preference storage system |
| #336 | Configure routing patterns | Trigger detection and routing |

**Dependency Order**: #332 → #335 → #333 → #334 → #336

## Open Questions (Resolved)

1. ~~Which automations for v1?~~ → Tier 1: Learning Loop, Work Logging, Issue Closure
2. ~~How do triggers work?~~ → Routing + slash commands, not code hooks
3. ~~What gets simplified?~~ → Remove internal refs, database deps, GitHub depth

## References

### Source Documents
- `wiki/Pongogo-to-Go-Workflows.md` - Full workflow catalog (33 triggers)
- `pongogo-to-go/docs/design/lifecycle-triggers.md` - PI lifecycle model
- `knowledge/instructions/` - Source instructions to extract from

### Related Issues (Super Pongogo)
- **Spike #295**: Core Loop Automation (this design)
- **Task #327**: Adaptive preference system implementation (P02)
- **Spike #328**: Context threshold hooks research (P05)
- **Spike #329**: Preferences system design with communication bundling (P03)
- **Task #330**: Extend PI system for glossary and FAQ candidates (P02)
- **Spike #331**: PM system detection in `pongogo init` (P05)
