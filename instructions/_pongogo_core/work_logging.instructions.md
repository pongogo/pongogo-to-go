---
id: core:work_logging
routing:
  protected: true
  priority: 10
  description: Basic work log format for progress tracking
  triggers:
    keywords:
      - work_log
      - log_entry
      - progress
      - accomplished
      - completed
      - done_for_today
      - session_end
      - wrap_up
      - friction_entry
      - correction_signal
    nlp: "Create work log entry to track progress, decisions, and friction events"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
evaluation:
  success_signals:
    - Entry follows format with TIME, TYPE, and description
    - Key decisions captured with rationale
    - Friction events logged immediately while context fresh
    - Entries specific enough to be useful later
  failure_signals:
    - Generic entries without specifics
    - Missing timestamp or type classification
    - Friction events not captured (lost learning opportunity)
    - Entries too verbose or too sparse
---

# Work Logging

**Purpose**: Track development progress and decisions with simple, consistent entries.

**Philosophy**: Work logs are living memory. Brief entries now save time later.

---

## When to Apply

This instruction triggers when:

- Significant work is completed (task, feature, fix)
- Key decision is made
- Session is ending
- Blocker is encountered or resolved
- **Friction signal detected** (user correction, "wait", "that's not what I") - log immediately
- User explicitly requests work log entry

---

## Preference-Aware Behavior

**Before executing**, check `.pongogo/preferences.yaml`:

```yaml
behaviors:
  work_log_on_task_completion:
    mode: auto | ask | skip
```

Follow the behavior mode per `_pongogo_collaboration.instructions.md`.

---

## Work Log Location

Store work logs in one of these locations (in order of preference):

1. **Project wiki**: `wiki/Work-Log-YYYY-MM.md` (if wiki exists)
2. **Docs folder**: `docs/work-log/YYYY-MM.md`
3. **Issue comment**: Add to relevant GitHub issue
4. **CHANGELOG.md**: If no other location configured

---

## Entry Format

### Basic Entry

```markdown
### [TIME] [TYPE] - Brief Title

Description of what was done.

**Key Decision**: [If applicable]
**Next Step**: [What comes next]
```

### Entry Types

<entry-types>
<type id="task" urgency="normal">
<use-for>Completing a task or feature</use-for>
<required-fields>What was done, key decision (if any), next step</required-fields>
</type>

<type id="decision" urgency="normal">
<use-for>Key architectural or design choice</use-for>
<required-fields>Context, options considered, choice made, rationale</required-fields>
</type>

<type id="blocker" urgency="high">
<use-for>Obstacle encountered or resolved</use-for>
<required-fields>Issue, root cause, resolution, time impact, prevention</required-fields>
</type>

<type id="learning" urgency="normal">
<use-for>Insight or pattern discovered</use-for>
<required-fields>Pattern, where it applies, evidence</required-fields>
</type>

<type id="friction" urgency="immediate">
<use-for>User correction signal (IMP-018)</use-for>
<required-fields>User signal, what I was doing, what user expected, prevention</required-fields>
<note>Log immediately while context is fresh - do not wait for task completion</note>
</type>

<type id="session" urgency="normal">
<use-for>End-of-session summary</use-for>
<required-fields>Completed items, blocked items, next session plan</required-fields>
</type>
</entry-types>

---

## Logging Workflow

<logging-workflow>
<step number="1" action="identify-trigger">
Determine what triggered logging need: task complete, decision made, friction signal, session end?
</step>

<step number="2" action="select-type">
Choose appropriate entry type from above. Friction entries are IMMEDIATE - don't wait.
</step>

<step number="3" action="get-timestamp">
Use current time. For friction, timestamp when event occurred, not when logged.
</step>

<step number="4" action="write-entry">
Follow format for entry type. Include required fields.
</step>

<step number="5" action="append-to-file">
Add to appropriate work log file (newest entries at top within each day).
</step>

<gate>Friction entries bypass normal workflow - log immediately when detected.</gate>
</logging-workflow>

---

## Examples

### Task Completion

```markdown
### 2:30 PM [task] - User auth refactor complete

Migrated authentication from sessions to JWT. Updated 12 API endpoints,
added refresh token rotation, and created migration script for existing sessions.

**Key Decision**: Using httpOnly cookies for refresh tokens (security)
**Next Step**: Update mobile app to use new auth flow
```

### Decision Entry

```markdown
### 10:15 AM [decision] - Database choice: PostgreSQL

Evaluated PostgreSQL vs MySQL for new service. Chose PostgreSQL for:
- Better JSON support for flexible schemas
- Native UUID type
- Team familiarity

**Trade-off**: Slightly more complex replication setup
**Evidence**: Benchmark showed 15% faster JSON queries
```

### Blocker Entry

```markdown
### 4:00 PM [blocker] - CI pipeline failing

**Issue**: Tests timing out on GitHub Actions
**Root Cause**: New integration tests hitting rate limits
**Resolution**: Added test API mocking, reduced parallel jobs

**Time Lost**: ~2 hours
**Prevention**: Add rate limit checks to test setup
```

### Learning Entry

```markdown
### 11:30 AM [learning] - Cache invalidation pattern

Discovered effective pattern for cache invalidation:
1. Use event-driven invalidation, not TTL
2. Publish cache-clear events on write
3. Subscribe in each service that caches

**Where This Applies**: Any multi-service cached data
**Evidence**: Reduced stale data issues by 90%
```

### Friction Entry (IMP-018)

```markdown
### 2:15 PM [friction] - Missing verification step

User said: "you're skipping the tests again"

**What I Was Doing**: Proceeding directly to implementation
**What User Expected**: Run tests before applying changes

**Mini-Retro**:
- Caused by: Optimization bias - tried to move fast
- Prevention: Add verification checkpoint before significant actions

**Implicit Guidance**: "Always run tests before applying changes"
**Occurrence**: 2nd (tracking for pattern)
```

**Note**: Log friction immediately while context is fresh. After 3+ occurrences of same type, consider promoting implicit guidance to standard preference.

### Session End

```markdown
### 5:45 PM [session] - End of day summary

**Completed**:
- User auth refactor (90%)
- Fixed 3 test failures
- Reviewed PR #42

**Blocked On**: Waiting for design review on settings page

**Tomorrow**: Finish auth, start settings implementation
```

---

## Bundling with Retrospective

If both work log and retrospective trigger:

1. Create combined entry
2. Include retrospective insights in work log
3. Single communication: "I've logged what we accomplished and captured the learnings."

```markdown
### 3:00 PM [task] - Feature X complete

Implemented feature X with Y approach.

**Retrospective**:
- Worked well: Incremental testing
- Challenging: API rate limits
- Next time: Mock external APIs earlier

**Evidence**: Commits abc123, def456
```

---

## File Organization

### Monthly Files

Organize by month for manageability:

```
docs/work-log/
├── 2025-01.md
├── 2025-02.md
└── 2025-03.md
```

### Within Each File

```markdown
# Work Log - January 2025

## January 15, 2025

### 4:30 PM [task] - Latest entry first
...

### 10:00 AM [decision] - Earlier entry
...

## January 14, 2025

### 5:00 PM [session] - End of day
...
```

**Note**: Newest entries at top (reverse chronological).

---

## Quick Reference

**Minimum viable entry**:
```markdown
### [TIME] [TYPE] - What was done
```

**Standard entry**:
```markdown
### [TIME] [TYPE] - Title

Description.

**Key Decision**: [If any]
**Next Step**: [What's next]
```

**Rich entry**:
```markdown
### [TIME] [TYPE] - Title

Description with context.

**Key Decision**: Choice and rationale
**Evidence**: Commits, files, links
**Next Step**: What comes next
**Retrospective**: [If applicable]
```

---

## Handling Uncertainty

<uncertainty-protocol>
If unsure what to log or how:

1. **When in doubt, log** - Better to have entry than miss important context
2. **Ask for clarity** - "Should I log this as a decision or a task?"
3. **State unknowns** - "Next step unclear - awaiting user input"

<common-uncertainties>
- Entry type unclear: Default to `task` if work was done, `decision` if choice was made
- Multiple things happened: Log separate entries or combine with clear sections
- Work log file doesn't exist: Create it following file organization pattern
</common-uncertainties>

<acceptable-responses>
- "I'll log this as a [type] entry. Does that capture it correctly?"
- "Several things happened this session. Should I create separate entries or combine them?"
</acceptable-responses>

<unacceptable-responses>
- Skipping logging because unsure of format
- Logging without timestamp
- Creating vague entries that won't be useful later
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="real-timestamps">Use actual current time, not guessed or approximate. Use MCP time server if available.</rule>
<rule id="specific-descriptions">Descriptions must reference specific work (files, commits, features). "Made progress" is not acceptable.</rule>
<rule id="friction-immediate">Friction entries MUST be logged immediately when detected. Context degrades rapidly.</rule>
<rule id="evidence-verifiable">Evidence (commits, files) must be real and verifiable. Don't reference commits that don't exist.</rule>
</grounding>

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Learning Loop](./learning_loop.instructions.md) - Retrospective capture
- [Issue Closure](./issue_closure.instructions.md) - Completion verification
