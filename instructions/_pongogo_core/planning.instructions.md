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
evaluation:
  success_signals:
    - Plan depth matches task complexity (quick/standard/deep)
    - Clear goal and success criteria defined before implementation
    - Risks identified and mitigation considered
    - User confirms approach before coding starts
  failure_signals:
    - Jumping to implementation without plan
    - Plan lacks definition of done
    - Over-planning simple tasks
    - Under-planning complex features
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

## Planning Workflow

<planning-workflow>
<step number="1" action="assess-complexity">
Determine plan depth needed: quick (&lt;1 hour task), standard (hours to days), deep (major feature).
</step>

<step number="2" action="gather-context">
Review existing code, related issues, user requirements. Don't plan in a vacuum.
</step>

<step number="3" action="answer-planning-questions">
Work through the four planning questions below. Document answers.
</step>

<step number="4" action="propose-approach">
Present approach to user with trade-offs. Wait for confirmation before implementing.
</step>

<step number="5" action="document-decisions">
Record significant decisions using decision template for future reference.
</step>

<gate>Do not start implementation until user confirms approach. Planning without buy-in wastes effort.</gate>
</planning-workflow>

---

## Planning Questions

<planning-questions>
<question id="goal" category="what">
<prompt>What are we trying to achieve?</prompt>
<sub-questions>
<item>What's the concrete goal?</item>
<item>What does success look like?</item>
<item>Who benefits from this?</item>
</sub-questions>
<output>Clear goal statement with measurable success criteria</output>
</question>

<question id="approaches" category="how">
<prompt>What approaches are available?</prompt>
<sub-questions>
<item>Option A: [approach and trade-offs]</item>
<item>Option B: [approach and trade-offs]</item>
<item>Which option best fits constraints?</item>
</sub-questions>
<output>Recommended approach with rationale</output>
</question>

<question id="constraints" category="limits">
<prompt>What are the constraints?</prompt>
<sub-questions>
<item>Technical constraints (existing code, APIs, infrastructure)</item>
<item>Resource constraints (time, scope)</item>
<item>Dependencies (other work that must complete first)</item>
</sub-questions>
<output>List of constraints that shape approach</output>
</question>

<question id="risks" category="what-if">
<prompt>What could go wrong?</prompt>
<sub-questions>
<item>Risks to mitigate</item>
<item>Edge cases to handle</item>
<item>Potential blockers</item>
</sub-questions>
<output>Risk register with mitigation strategies</output>
</question>
</planning-questions>

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

## Thinking vs Output Separation

<thinking-output-structure>
When planning, separate internal reasoning from presented output:

<thinking>
Use this section to:
- Work through planning questions internally
- Evaluate trade-offs between options
- Consider risks and edge cases
- Form recommendation
</thinking>

<plan-output>
Present to user:
- Clear goal and approach
- Trade-offs considered
- Recommended path with rationale
- Request for confirmation
</plan-output>

**Why separate?** Clear thinking improves plan quality. Clean output improves user understanding. Mixed thinking/output causes confusion.
</thinking-output-structure>

---

## Handling Uncertainty

<uncertainty-protocol>
If requirements are unclear:

1. **Identify gaps** - What information is missing to plan effectively?
2. **Ask specific questions** - Don't assume; request clarification
3. **State assumptions** - If proceeding with assumptions, make them explicit
4. **Propose options** - If multiple approaches possible, present choices

<acceptable-responses>
- "To plan this effectively, I need to understand: [specific questions]. Can you clarify?"
- "I see two possible interpretations of the goal. Did you mean A or B?"
- "I'm proceeding with the assumption that [X]. Please correct if wrong."
</acceptable-responses>

<unacceptable-responses>
- Planning with unstated assumptions
- Recommending approach without understanding goal
- Skipping constraint analysis due to incomplete info
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="user-requirements-only">Base plan on explicitly stated requirements. Do not add features or scope not requested.</rule>
<rule id="verify-constraints">Confirm technical constraints by examining existing code. Don't assume architecture.</rule>
<rule id="confirm-before-implement">Always get user confirmation on approach before starting implementation. No "I'll just start and see."</rule>
<rule id="document-decisions">Record significant decisions with rationale. Plans without documented reasoning are hard to revisit.</rule>
</grounding>

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Approach commitment
- [Work Logging](./work_logging.instructions.md) - Decision documentation
- [Issue Closure](./issue_closure.instructions.md) - Definition of done
