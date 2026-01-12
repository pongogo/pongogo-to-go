---
id: core:issue_closure
routing:
  protected: true
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
evaluation:
  success_signals:
    - Completion comment follows template structure
    - Evidence section populated with actual commits/tests
    - Issue not closed with unmet acceptance criteria
    - Uncertainty explicitly stated when verification blocked
  failure_signals:
    - Issue closed without completion comment
    - Missing evidence links
    - Acceptance criteria not verified before closure
    - Assumed completion without explicit verification
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

<closure-checklist>
<category name="deliverables">
<check id="acceptance-criteria" required="true">All acceptance criteria met</check>
<check id="code-committed" required="true">Code changes committed and pushed</check>
<check id="tests-passing" required="conditional">Tests passing (if applicable)</check>
<check id="docs-updated" required="conditional">Documentation updated (if applicable)</check>
</category>

<category name="quality">
<check id="no-bugs" required="true">No known bugs introduced</check>
<check id="no-breaking" required="true">No breaking changes (or documented if intentional)</check>
<check id="code-reviewed" required="conditional">Code reviewed (if required)</check>
</category>

<category name="learning">
<check id="work-log" required="conditional">Work log entry created (if `work_log_on_task_completion` not `skip`)</check>
<check id="decisions-documented" required="true">Key decisions documented</check>
<check id="patterns-noted" required="false">Patterns noted for future reference</check>
</category>

<category name="issue-update">
<check id="completion-comment" required="true">Completion comment added summarizing work</check>
<check id="related-linked" required="false">Related issues linked or updated</check>
<check id="status-done" required="true">Status moved to Done</check>
</category>
</closure-checklist>

**Required checks** (`required="true"`) must pass before closure. **Conditional checks** depend on project configuration. **Optional checks** are best practice but not blocking.

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

<closure-flow type="standard">
<step number="1" action="verify-deliverables">Check all acceptance criteria against issue body</step>
<step number="2" action="run-checklist">Execute closure checklist (all required checks must pass)</step>
<step number="3" action="add-comment">Add completion comment using template below</step>
<step number="4" action="capture-learning">Run quick retrospective (if configured in preferences)</step>
<step number="5" action="close-issue">Move status to Done</step>
<gate>All steps must complete. If any step fails, stop and report which step blocked closure.</gate>
</closure-flow>

<closure-flow type="quick" applies-to="small-tasks">
<step number="1" action="verify-done">Confirm acceptance criteria met</step>
<step number="2" action="add-comment">Add brief comment: "Completed: [summary]"</step>
<step number="3" action="close-issue">Move status to Done</step>
<gate>Use only for tasks with &lt;3 acceptance criteria and no code changes.</gate>
</closure-flow>

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

## Handling Uncertainty

<uncertainty-protocol>
If you cannot verify completion:

1. **State explicitly** which checklist items cannot be verified and why
2. **Ask user** for clarification rather than assuming completion
3. **Never close** an issue if verification is blocked
4. **Document blockers** in a status update comment

<acceptable-responses>
- "I cannot verify [check-id] because [reason]. Please confirm or provide evidence."
- "Acceptance criteria unclear. The issue states [X] but I need clarification on [Y]."
- "Tests status unknown - no test output available. Should I run tests or mark as verified?"
</acceptable-responses>

<unacceptable-responses>
- Assuming criteria are met without verification
- Closing issue with unverified checklist items
- Inferring completion from partial evidence
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="acceptance-criteria">Only reference acceptance criteria explicitly stated in the issue body. Do not infer or assume criteria not written.</rule>
<rule id="evidence-required">Evidence must be actual artifacts (commit SHAs, test output, PR links). Do not fabricate or assume evidence exists.</rule>
<rule id="status-verification">Verify current issue status from GitHub before updating. Do not assume status based on conversation history.</rule>
</grounding>

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
