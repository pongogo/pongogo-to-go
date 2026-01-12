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
evaluation:
  success_signals:
    - Issue follows appropriate template for type
    - Title matches format [Type]-brief_description
    - Acceptance criteria are specific and verifiable
    - All template sections filled with real content (no placeholders)
  failure_signals:
    - Missing acceptance criteria
    - Vague descriptions like "improve X" without specifics
    - Template sections left as placeholders
    - Wrong issue type for the work
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

<issue-types>
<type id="task" label="task">
<use-for>Single unit of work with clear deliverables</use-for>
<indicators>Concrete outcome, can be completed in one session to a few days</indicators>
</type>

<type id="epic" label="epic">
<use-for>Multi-task initiative requiring breakdown</use-for>
<indicators>Multiple deliverables, requires sub-issues, spans multiple work sessions</indicators>
</type>

<type id="bug" label="bug">
<use-for>Defect requiring fix</use-for>
<indicators>Something broken, unexpected behavior, regression</indicators>
</type>

<type id="spike" label="spike">
<use-for>Research or investigation with time-box</use-for>
<indicators>Unknown solution, needs exploration, learning-focused</indicators>
</type>
</issue-types>

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

## Creation Flow

<creation-flow>
<step number="1" action="determine-type">
Identify issue type based on indicators above. If unclear, ask user.
</step>

<step number="2" action="gather-requirements">
Collect: goal, context, deliverables, acceptance criteria.
If any are missing, ask user before proceeding.
</step>

<step number="3" action="draft-issue">
Apply appropriate template. Fill ALL sections with real content.
</step>

<step number="4" action="validate-quality">
Check against quality criteria below. Fix any issues before creating.
</step>

<step number="5" action="create-issue">
Create issue via GitHub. Apply labels. Assign milestone if applicable.
</step>

<gate>Do not skip steps. If step 2 reveals missing information, pause and ask.</gate>
</creation-flow>

---

## Issue Quality Criteria

<quality-criteria>
<criterion id="specific-goal">Goal states concrete outcome, not vague direction</criterion>
<criterion id="verifiable-criteria">Each acceptance criterion can be objectively verified</criterion>
<criterion id="no-placeholders">All template sections contain real content, no TBD/TODO</criterion>
<criterion id="appropriate-scope">Task is single unit; Epic is broken down; Spike has time-box</criterion>
<criterion id="context-provided">Reader can understand why this work matters</criterion>
</quality-criteria>

---

## Handling Uncertainty

<uncertainty-protocol>
If user request lacks sufficient detail:

1. **Do not assume** - Ask for clarification rather than inferring requirements
2. **Identify gaps** - State specifically what information is missing
3. **Propose options** - If type is ambiguous, present options with reasoning

<acceptable-responses>
- "To create this issue, I need: [specific missing info]. Can you provide that?"
- "This could be a Task or Spike. Task if solution is known, Spike if we need to research first. Which fits?"
- "The acceptance criteria are vague. Can you specify what 'improved' means concretely?"
</acceptable-responses>

<unacceptable-responses>
- Creating issue with placeholder content
- Assuming acceptance criteria not stated by user
- Guessing issue type without confirming
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="user-stated-only">Only include requirements explicitly stated by user. Do not infer or add requirements.</rule>
<rule id="no-placeholders">Never create issues with TBD, TODO, or placeholder text. Get real content first.</rule>
<rule id="verify-type">Confirm issue type matches the work. A research question is a Spike, not a Task.</rule>
</grounding>

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

### Example 3: Spike Issue

**Title**: `[Spike]-evaluate_auth_providers`

```markdown
## Research Question

Which authentication provider best fits our requirements for SSO and MFA support?

## Context

Current auth is custom-built and lacks SSO. Enterprise customers requesting SSO.

## Scope

- Include: Auth0, Okta, Firebase Auth, Clerk
- Exclude: Self-hosted solutions, custom SAML implementation

## Expected Deliverables

- [ ] Comparison matrix (features, pricing, integration effort)
- [ ] Recommendation with rationale
- [ ] Next steps for implementation

## Time Box

4 hours maximum. Report findings even if incomplete.
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
