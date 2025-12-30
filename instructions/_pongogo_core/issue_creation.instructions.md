---
id: core:issue_creation
routing:
  protected: true
  priority: 10
  description: Guide GitHub issue creation with templates
  triggers:
    keywords:
      - create_issue
      - new_issue
      - open_issue
      - file_issue
      - track_this
      - make_a_ticket
      - needs_an_issue
    nlp: "Create a new GitHub issue to track work"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
  conditional:
    requires: github_pm  # Only active if GitHub PM detected
---

# Issue Creation

**Purpose**: Guide consistent GitHub issue creation.

**Philosophy**: Good issues save time. Clear description, clear scope, clear done.

**Conditional**: This instruction only activates if GitHub PM is detected during `pongogo init`.

---

## When to Apply

This instruction triggers when:

- User wants to track work as a GitHub issue
- New feature, bug, or task needs to be formalized
- User says "create an issue for this" or "we should track this"

---

## Issue Types

| Type | Use For | Label |
|------|---------|-------|
| **Task** | Single unit of work | `task` |
| **Epic** | Multi-task initiative | `epic` |
| **Bug** | Defect to fix | `bug` |
| **Spike** | Research/investigation | `spike` |

---

## Issue Title Format

```
[Type]-brief_description
```

Examples:
- `[Task]-add_user_authentication`
- `[Epic]-payment_integration`
- `[Bug]-login_redirect_loop`
- `[Spike]-evaluate_database_options`

---

## Issue Body Template

### Task Template

```markdown
## Goal

Brief description of what this task accomplishes.

## Context

Why this is needed and any relevant background.

## Deliverables

- [ ] Deliverable 1
- [ ] Deliverable 2
- [ ] Deliverable 3

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2

## Notes

Any additional context, links, or considerations.
```

### Bug Template

```markdown
## Bug Description

Brief description of the issue.

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Environment

- OS:
- Browser/Runtime:
- Version:

## Additional Context

Screenshots, logs, related issues.
```

### Spike Template

```markdown
## Research Question

What we need to learn or evaluate.

## Context

Why this research is needed.

## Scope

- Include: what to investigate
- Exclude: what's out of scope

## Expected Deliverables

- [ ] Findings document
- [ ] Recommendation
- [ ] Next steps identified

## Time Box

Maximum time to spend before reporting findings.
```

---

## Labels

Apply appropriate labels:

| Label | When |
|-------|------|
| `task` | Single work unit |
| `epic` | Multi-task initiative |
| `bug` | Defect |
| `spike` | Research |
| `priority:high` | Urgent |
| `blocked` | Has dependencies |

---

## Milestone Assignment

Assign to milestone if:
- Work is part of current roadmap
- Milestone exists for the work stream

Leave unassigned if:
- Exploratory work
- Not yet prioritized
- Backlog item for later

---

## Examples

### Example 1: Task Issue

**Title**: `[Task]-add_logout_button`

```markdown
## Goal

Add logout functionality to the navigation.

## Context

Users currently can't log out without clearing cookies manually.

## Deliverables

- [ ] Logout button in nav header
- [ ] Session clearing on click
- [ ] Redirect to login page

## Acceptance Criteria

- [ ] Clicking logout clears session
- [ ] User redirected to /login
- [ ] Button styled consistently with nav
```

### Example 2: Bug Issue

**Title**: `[Bug]-login_redirect_loop`

```markdown
## Bug Description

Users get stuck in redirect loop after login.

## Steps to Reproduce

1. Go to /login
2. Enter valid credentials
3. Click submit
4. Observe redirect loop

## Expected Behavior

Redirect to dashboard after login.

## Actual Behavior

Infinite redirect between /login and /callback.

## Environment

- OS: macOS 14
- Browser: Chrome 120
- Version: 2.1.0
```

---

## Quick Issue Creation

For simple issues, minimal format:

**Title**: `[Task]-brief_description`

**Body**:
```markdown
Brief description of the work.

- [ ] What needs to be done
```

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Issue Closure](./issue_closure.instructions.md) - Completing issues
- [Issue Status](./issue_status.instructions.md) - Tracking progress
