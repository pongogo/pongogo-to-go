---
id: core:issue_status
routing:
  protected: true
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
evaluation:
  success_signals:
    - Status matches actual work state
    - Transition comment explains context
    - Blockers include what's needed to unblock
    - No stale In Progress items (>3 days without update)
  failure_signals:
    - Status doesn't reflect reality
    - Transition without comment
    - Blocked status without unblock path
    - Multiple concurrent In Progress items
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

<status-definitions>
<status id="backlog" order="1">
<meaning>Not yet started</meaning>
<when-to-use>Default for new issues not yet prioritized</when-to-use>
<indicator>No work has begun; issue is queued</indicator>
</status>

<status id="up-next" order="2">
<meaning>Prioritized for soon</meaning>
<when-to-use>Next items to work on after current work</when-to-use>
<indicator>Work will begin when capacity available</indicator>
</status>

<status id="in-progress" order="3">
<meaning>Actively working</meaning>
<when-to-use>Currently being implemented</when-to-use>
<indicator>Code being written, research happening, deliverables in progress</indicator>
<constraint>Limit to ONE issue per person at a time for focus</constraint>
</status>

<status id="on-hold" order="4">
<meaning>Paused temporarily</meaning>
<when-to-use>Waiting on external factor not blocking (e.g., scheduled dependency)</when-to-use>
<indicator>Work paused by choice, will resume at known time</indicator>
</status>

<status id="blocked" order="5">
<meaning>Cannot proceed</meaning>
<when-to-use>Dependency or issue preventing progress</when-to-use>
<indicator>Cannot continue without external resolution</indicator>
<required-info>Must specify what's blocking and path to unblock</required-info>
</status>

<status id="ready-for-review" order="6">
<meaning>Work complete, awaiting review</meaning>
<when-to-use>Implementation done, needs approval before closing</when-to-use>
<indicator>Deliverables ready, PR open, waiting for feedback</indicator>
</status>

<status id="done" order="7">
<meaning>Finished</meaning>
<when-to-use>All acceptance criteria met, verified complete</when-to-use>
<indicator>Issue can be closed</indicator>
<reference>See issue_closure.instructions.md for closure checklist</reference>
</status>
</status-definitions>

---

## Status Transitions

<transitions>
<transition id="start-work" from="backlog,up-next" to="in-progress">
<trigger>Beginning active work on issue</trigger>
<actions>
<action required="true">Update issue status to "In Progress"</action>
<action required="true">Add comment with approach and expected work</action>
<action required="false">Note any initial blockers or dependencies</action>
</actions>
<gate>Verify no other issues already In Progress (focus constraint)</gate>
</transition>

<transition id="hit-blocker" from="in-progress" to="blocked">
<trigger>Cannot proceed due to external dependency</trigger>
<actions>
<action required="true">Update status to "Blocked"</action>
<action required="true">Add comment explaining what's blocking</action>
<action required="true">Specify what's needed to unblock</action>
<action required="false">Tag person/issue that can resolve</action>
</actions>
<gate>Must include unblock path - don't block without resolution plan</gate>
</transition>

<transition id="unblock" from="blocked" to="in-progress">
<trigger>Blocker resolved, work can resume</trigger>
<actions>
<action required="true">Update status to "In Progress"</action>
<action required="true">Add comment explaining how blocker was resolved</action>
</actions>
</transition>

<transition id="pause-work" from="in-progress" to="on-hold">
<trigger>Pausing by choice (not blocked)</trigger>
<actions>
<action required="true">Update status to "On Hold"</action>
<action required="true">Add comment with reason for pause</action>
<action required="true">Document current progress state</action>
<action required="true">Note when expected to resume</action>
</actions>
</transition>

<transition id="ready-review" from="in-progress" to="ready-for-review">
<trigger>Work complete, needs review before closure</trigger>
<actions>
<action required="true">Update status to "Ready for Review"</action>
<action required="true">Add comment summarizing work done</action>
<action required="conditional">Link PR if applicable</action>
<action required="true">Specify what needs to be verified</action>
</actions>
</transition>

<transition id="complete" from="ready-for-review" to="done">
<trigger>Review complete, acceptance criteria verified</trigger>
<actions>
<action required="true">Follow issue_closure.instructions.md checklist</action>
<action required="true">Update status to "Done"</action>
<action required="true">Add completion comment</action>
</actions>
<reference>See issue_closure.instructions.md for full closure process</reference>
</transition>
</transitions>

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

## Handling Uncertainty

<uncertainty-protocol>
If correct status is ambiguous:

1. **Check current state** - Verify actual issue status from GitHub before updating
2. **Clarify with user** - Ask which status reflects reality
3. **Default conservatively** - If unsure between In Progress and Blocked, ask rather than assume

<status-decision-tree>
<question>Is external dependency preventing progress?</question>
<yes>Blocked (requires unblock path)</yes>
<no>
  <question>Is work paused by choice with known resume time?</question>
  <yes>On Hold</yes>
  <no>
    <question>Is work actively happening right now?</question>
    <yes>In Progress</yes>
    <no>Ask user for clarification</no>
  </no>
</no>
</status-decision-tree>

<acceptable-responses>
- "The issue says In Progress but no work has happened in 5 days. Should this be On Hold or Blocked?"
- "I'm unclear if this is blocked or just waiting. Is there an external dependency, or is this by choice?"
</acceptable-responses>

<unacceptable-responses>
- Assuming status without checking GitHub
- Changing status without appropriate comment
- Marking Blocked without specifying unblock path
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="verify-before-update">Always check current status from GitHub before updating. Don't assume status from conversation history.</rule>
<rule id="one-in-progress">Enforce focus: only ONE issue should be In Progress per person. If starting new work, verify nothing else is In Progress.</rule>
<rule id="blocked-requires-path">Never mark Blocked without specifying what's blocking AND what's needed to unblock. Blocked without path = stuck forever.</rule>
<rule id="comment-every-transition">Every status transition requires a comment. Silent transitions lose context.</rule>
</grounding>

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
