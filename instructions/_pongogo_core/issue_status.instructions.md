---
routing:
  priority: 10
  description: Manage GitHub issue status transitions
  triggers:
    keywords:
      - status_update
      - move_to_progress
      - start_work
      - mark_blocked
      - unblock
      - ready_for_review
      - on_hold
      - resume_work
    nlp: "Update GitHub issue status or project board column"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
  conditional:
    requires: github_pm  # Only active if GitHub PM detected
---

# Issue Status Management

**Purpose**: Guide GitHub issue status transitions on project boards.

**Philosophy**: Status should reflect reality. Update as work progresses.

**Conditional**: This instruction only activates if GitHub PM is detected during `pongogo init`.

---

## When to Apply

This instruction triggers when:

- Starting work on an issue
- Work is blocked or unblocked
- Ready for review
- Putting work on hold
- Resuming work

---

## Status Values

| Status | Meaning | When to Use |
|--------|---------|-------------|
| **Backlog** | Not yet started | Default for new issues |
| **Up Next** | Prioritized for soon | Next items to work on |
| **In Progress** | Actively working | Currently being implemented |
| **On Hold** | Paused temporarily | Waiting on external factor |
| **Blocked** | Cannot proceed | Dependency or issue preventing progress |
| **Ready for Review** | Work complete | Awaiting review/approval |
| **Done** | Finished | All acceptance criteria met |

---

## Status Transitions

### Starting Work

```
Backlog/Up Next → In Progress
```

Actions:
- Update issue status to "In Progress"
- Add comment: "Starting work on this"
- Note any initial approach

### Hitting a Blocker

```
In Progress → Blocked
```

Actions:
- Update status to "Blocked"
- Add comment explaining:
  - What's blocking
  - What's needed to unblock
  - Who can help (if known)

### Resuming After Block

```
Blocked → In Progress
```

Actions:
- Update status to "In Progress"
- Add comment: "Unblocked - [how it was resolved]"

### Pausing Work

```
In Progress → On Hold
```

Actions:
- Update status to "On Hold"
- Add comment explaining:
  - Why paused
  - When expected to resume
  - Current progress state

### Ready for Review

```
In Progress → Ready for Review
```

Actions:
- Update status to "Ready for Review"
- Add comment with:
  - Summary of work done
  - Link to PR if applicable
  - What needs review

### Completing Work

```
Ready for Review → Done
```

Actions:
- See `issue_closure.instructions.md` for full checklist
- Update status to "Done"
- Add completion comment

---

## Comment Templates

### Starting Work

```markdown
🚀 Starting work on this.

**Approach**: Brief description of how I'll tackle this.

**Expected completion**: [estimate if known]
```

### Blocked

```markdown
🚧 Blocked

**Blocking issue**: What's preventing progress

**Needed to unblock**: What needs to happen

**Related**: #issue-number or @person
```

### Unblocked

```markdown
✅ Unblocked

**Resolution**: How the blocker was resolved

Resuming work.
```

### On Hold

```markdown
⏸️ Putting on hold

**Reason**: Why pausing

**Current state**: What's been done so far

**Resume when**: Expected trigger to resume
```

### Ready for Review

```markdown
👀 Ready for review

**Summary**: What was implemented

**PR**: #pr-number (if applicable)

**To verify**:
- [ ] Check 1
- [ ] Check 2
```

---

## Project Board Updates

If using GitHub Projects:

1. Status field maps to board columns
2. Update via issue comment or directly on board
3. Automations may move cards based on labels/status

**Manual update**:
```
gh project item-edit --owner ORG --project PROJECT --id ITEM_ID --field-id STATUS_FIELD_ID --single-select-option-id OPTION_ID
```

---

## Best Practices

### Do

- Update status as soon as state changes
- Add context in status comments
- Link related issues/PRs
- Be honest about blockers

### Don't

- Leave issues in stale states
- Mark "In Progress" and forget
- Skip status updates for speed
- Have multiple "In Progress" items (focus!)

---

## Examples

### Example: Full Workflow

```markdown
# Issue #42: Add user settings page

---
🚀 Starting work on this.

**Approach**: Creating new /settings route with React component

---
🚧 Blocked

**Blocking issue**: Need design mockups for settings layout
**Needed to unblock**: Mockups from design team
**Related**: @designer

---
✅ Unblocked

Design mockups received. Resuming implementation.

---
👀 Ready for review

**Summary**: Implemented settings page with profile and preferences tabs.

**PR**: #45

**To verify**:
- [ ] Profile updates save correctly
- [ ] Preferences persist across sessions
- [ ] Responsive on mobile

---
## Completed ✅

[See closure comment]
```

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Issue Creation](./issue_creation.instructions.md) - Creating new issues
- [Issue Closure](./issue_closure.instructions.md) - Completing issues
