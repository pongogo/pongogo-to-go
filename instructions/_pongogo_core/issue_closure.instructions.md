---
routing:
  priority: 10
  description: Completion verification for GitHub issues
  triggers:
    keywords:
      - close_issue
      - issue_closure
      - done
      - complete
      - ready_to_close
      - mark_done
      - finish_task
      - shipped
      - close_this
      - mark_complete
    nlp: "Verify work is complete before closing GitHub issue"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
  conditional:
    requires: github_pm  # Only active if GitHub PM detected
---

# Issue Closure

**Purpose**: Verify work is complete before closing GitHub issues.

**Philosophy**: Completion ≠ Closure. Verify deliverables before marking done.

**Conditional**: This instruction only activates if GitHub PM is detected during `pongogo init`.

---

## When to Apply

This instruction triggers when:

- Work is complete and ready to close issue
- User says "done", "complete", "close this", "mark done", "shipped"
- All acceptance criteria appear met
- Ready to move issue to Done status

---

## Preference-Aware Behavior

**Before executing**, check `.pongogo/preferences.yaml`:

```yaml
behaviors:
  issue_closure:
    mode: auto | ask | skip
```

Follow the behavior mode per `_pongogo_collaboration.instructions.md`.

---

## Closure Checklist

### 1. Deliverables Complete

- [ ] All acceptance criteria met
- [ ] Code changes committed and pushed
- [ ] Tests passing (if applicable)
- [ ] Documentation updated (if applicable)

### 2. Quality Verified

- [ ] No known bugs introduced
- [ ] No breaking changes (or documented if intentional)
- [ ] Code reviewed (if required)

### 3. Learning Captured

- [ ] Work log entry created (if `work_log_on_task_completion` not `skip`)
- [ ] Key decisions documented
- [ ] Patterns noted for future reference

### 4. Issue Updated

- [ ] Completion comment added summarizing work
- [ ] Related issues linked or updated
- [ ] Status moved to Done

---

## Completion Comment Template

```markdown
## Completed

**Summary**: Brief description of what was done

**Deliverables**:
- [ ] Item 1 - Done
- [ ] Item 2 - Done

**Key Changes**:
- File/component changed
- New functionality added

**Evidence**:
- Commits: [links]
- Tests: [passing/added]
- Docs: [updated]

**Notes**: Any important context for future reference
```

---

## Closure Flow

### Standard Flow

1. **Verify deliverables** - Check all acceptance criteria
2. **Run checklist** - Go through closure checklist above
3. **Add completion comment** - Document what was done
4. **Capture learning** - Quick retrospective (if configured)
5. **Close issue** - Move to Done status

### Quick Flow (for small tasks)

1. **Verify done** - Acceptance criteria met?
2. **Add brief comment** - "Completed: [summary]"
3. **Close issue**

---

## What NOT to Close

Do not close if:

- **Acceptance criteria unmet**: Any required item missing
- **Tests failing**: Unless explicitly acceptable
- **Blocking issues exist**: Dependencies not resolved
- **User approval needed**: Work requires review first

In these cases:
- Update issue with current status
- List what's remaining
- Keep issue open

---

## Examples

### Example 1: Standard Closure

```markdown
## Completed

**Summary**: Implemented user authentication with JWT

**Deliverables**:
- [x] JWT token generation
- [x] Token validation middleware
- [x] Refresh token rotation
- [x] Updated 12 API endpoints

**Key Changes**:
- `src/auth/` - New auth module
- `src/middleware/auth.ts` - Validation middleware
- `src/routes/*.ts` - Protected endpoints

**Evidence**:
- Commits: abc123, def456
- Tests: 15 new, all passing
- Docs: Updated API.md

**Notes**: Mobile app needs update to use new auth flow (tracked in #123)
```

### Example 2: Quick Closure

```markdown
Completed: Fixed login timeout by increasing session duration to 24h.

Commit: abc123
```

### Example 3: Partial Completion

```markdown
## Status Update (not closing)

**Completed**:
- [x] JWT token generation
- [x] Token validation middleware

**Remaining**:
- [ ] Refresh token rotation
- [ ] Update API endpoints

**Blocked by**: Waiting for design decision on token storage (#456)

**ETA**: Ready to complete once #456 resolved
```

---

## Integration with Learning Loop

Before closing:

1. Check if retrospective should run (per preferences)
2. If yes, run quick 4-question retrospective
3. Include insights in completion comment
4. Then close issue

Bundle communication:
> "I've verified the work is complete, captured the learnings, and closed the issue."

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Learning Loop](./learning_loop.instructions.md) - Retrospective before closure
- [Work Logging](./work_logging.instructions.md) - Progress documentation
