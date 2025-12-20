---
routing:
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
    nlp: "Create work log entry to track progress and decisions"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
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

| Type | Use For |
|------|--------|
| `task` | Completing a task or feature |
| `decision` | Key architectural or design choice |
| `blocker` | Obstacle encountered or resolved |
| `learning` | Insight or pattern discovered |
| `session` | End-of-session summary |

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

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Learning Loop](./learning_loop.instructions.md) - Retrospective capture
- [Issue Closure](./issue_closure.instructions.md) - Completion verification
