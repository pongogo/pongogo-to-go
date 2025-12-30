---
id: core:planning
routing:
  protected: true
  priority: 10
  description: Guide planning and design discussions
  triggers:
    keywords:
      - plan
      - planning
      - design
      - approach
      - architecture
      - strategy
      - think_through
      - let_me_plan
      - how_should_we
      - what_approach
      - lets_think_about
      - before_we_start
    nlp: "Plan approach or design for implementation work"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
---

# Planning & Design

**Purpose**: Guide structured planning before implementation.

**Philosophy**: Good planning prevents rework. Think before coding.

---

## When to Apply

This instruction triggers when:

- Starting a new feature or significant change
- User asks "how should we approach this?"
- Before implementing something non-trivial
- Design decisions need to be made

---

## Planning Questions

### 1. What Are We Trying to Achieve?

- What's the goal?
- What does success look like?
- Who benefits from this?

### 2. What Approaches Are Available?

- Option A: [approach]
- Option B: [approach]
- Trade-offs between them

### 3. What Are the Constraints?

- Technical constraints
- Time/resource constraints
- Dependencies on other work

### 4. What Could Go Wrong?

- Risks to consider
- Edge cases to handle
- Potential blockers

---

## Simple Planning Template

```markdown
## Plan: [Feature/Task Name]

**Goal**: What we're trying to achieve

**Approach**: How we'll do it

**Steps**:
1. First step
2. Second step
3. Third step

**Considerations**:
- Risk/edge case 1
- Risk/edge case 2

**Definition of Done**:
- [ ] Criteria 1
- [ ] Criteria 2
```

---

## Approach Commitment

If user has committed approaches in preferences:

```yaml
approaches:
  debugging:
    technique: "Reproduce first, then investigate"
```

Apply the committed approach:
```
"I'll use the 'reproduce first' approach we've been using for debugging."
```

---

## Quick vs Deep Planning

### Quick Plan (5 min)

For small tasks:
- Goal in one sentence
- Approach in one sentence
- Start implementing

### Standard Plan (15-30 min)

For medium features:
- Use planning template above
- Identify 2-3 key decisions
- Document approach briefly

### Deep Plan (1+ hour)

For major features or architecture:
- Full design document
- Multiple stakeholder input
- Prototype if needed
- Formal review

---

## Decision Documentation

For significant decisions during planning:

```markdown
### Decision: [Topic]

**Context**: Why this decision is needed

**Options Considered**:
1. Option A - pros/cons
2. Option B - pros/cons

**Decision**: Chose Option X

**Rationale**: Why this option was selected
```

---

## Examples

### Example 1: Quick Plan

> **Goal**: Add logout button to nav
>
> **Approach**: Add button to existing nav component, call auth.logout()
>
> Starting implementation...

### Example 2: Standard Plan

```markdown
## Plan: User Settings Page

**Goal**: Allow users to update their profile and preferences

**Approach**: Create new settings route with tabbed interface

**Steps**:
1. Create /settings route and component
2. Add profile tab (name, email, avatar)
3. Add preferences tab (notifications, theme)
4. Add API endpoints for updates
5. Add validation and error handling

**Considerations**:
- Email changes need verification flow
- Avatar upload needs size limits
- Some settings may need confirmation

**Definition of Done**:
- [ ] All tabs functional
- [ ] Form validation working
- [ ] Error states handled
- [ ] Tests added
```

### Example 3: Design Decision

```markdown
### Decision: State Management Approach

**Context**: Need state management for user preferences

**Options Considered**:
1. React Context - Simple, no dependencies, limited DevTools
2. Redux - Powerful, good DevTools, more boilerplate
3. Zustand - Simple API, good DX, smaller bundle

**Decision**: Zustand

**Rationale**:
- Simpler than Redux for our use case
- Better DX than Context for debugging
- Team prefers minimal boilerplate
```

---

## Anti-Patterns

### Over-Planning

Signs of over-planning:
- Planning document longer than implementation
- Designing for hypothetical future requirements
- Paralysis by analysis

**Fix**: Start simple, iterate based on real feedback

### Under-Planning

Signs of under-planning:
- Constant rework during implementation
- Discovering requirements mid-implementation
- Architecture changes after 50% complete

**Fix**: Spend proportional time planning (10-20% of task time)

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Approach commitment
- [Work Logging](./work_logging.instructions.md) - Decision documentation
- [Issue Closure](./issue_closure.instructions.md) - Definition of done
