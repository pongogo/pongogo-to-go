---
id: core:pi_tracking
routing:
  protected: true
  priority: 10
  description: Pattern detection and threshold-based improvement tracking
  triggers:
    keywords:
      - pattern
      - recurring
      - improvement
      - third_time
      - keeps_happening
      - same_issue
      - noticed_pattern
    nlp: "Track recurring patterns and suggest improvements at threshold"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
---

# Pattern Improvement Tracking

**Purpose**: Track recurring patterns and suggest action when threshold (3+) is reached.

**Philosophy**: The third time isn't an accident - it's a pattern worth addressing.

---

## When to Apply

This instruction triggers when:

- Same issue/pattern appears for 3rd+ time
- During retrospectives when patterns noticed
- User mentions "this keeps happening" or "again"
- Recognizing recurring technical debt or workflow issues

---

## Preference-Aware Behavior

**Before executing**, check `.pongogo/preferences.yaml`:

```yaml
behaviors:
  pi_threshold_prompt:
    mode: auto | ask | skip
```

Follow the behavior mode per `_pongogo_collaboration.instructions.md`.

---

## The 3-Occurrence Rule

| Count | Action | Confidence |
|-------|--------|------------|
| 1st | Note it, move on | Low - might be one-off |
| 2nd | Track it, watch for more | Medium - emerging pattern |
| 3rd+ | Suggest action | High - validated pattern |

### Why 3?

- Once is an incident
- Twice is coincidence  
- Three times is a pattern

The third occurrence provides enough evidence to justify investing time in a solution.

---

## Tracking Patterns

### Simple Tracking (File-Based)

Create `.pongogo/patterns.md`:

```markdown
# Pattern Tracking

## Active Patterns

### Test timeout issues
- **Count**: 2
- **First seen**: 2025-01-15
- **Last seen**: 2025-01-20
- **Context**: Integration tests hitting external APIs
- **Potential fix**: Add API mocking

### Missing error handling
- **Count**: 3 ✅ THRESHOLD
- **First seen**: 2025-01-10
- **Last seen**: 2025-01-22
- **Context**: API endpoints returning 500 instead of proper errors
- **Action taken**: Created error handling instruction file

## Resolved Patterns

### Database connection pooling
- **Final count**: 4
- **Resolution**: Added connection pool config
- **Date resolved**: 2025-01-18
```

### Pattern Entry Format

```markdown
### [Pattern Name]
- **Count**: N
- **First seen**: YYYY-MM-DD
- **Last seen**: YYYY-MM-DD
- **Context**: Where/when this occurs
- **Potential fix**: Proposed solution
- **Action taken**: [Once resolved]
```

---

## Threshold Actions

When a pattern reaches 3+ occurrences:

### Option 1: Create Instruction File

For process/workflow patterns:

```markdown
"I've noticed [pattern] has occurred 3 times now.
Want me to create an instruction file to prevent this?"
```

### Option 2: Add to Documentation

For knowledge gaps:

```markdown
"This [issue] keeps coming up. Should I add it to the
project documentation so it's easier to find?"
```

### Option 3: Create Checklist

For repeated oversights:

```markdown
"We've missed [thing] 3 times. Want me to create a
checklist to catch this earlier?"
```

### Option 4: Technical Fix

For recurring bugs/issues:

```markdown
"This [problem] has happened 3 times. Should we
prioritize a proper fix? I can create an issue for it."
```

---

## Pattern Types

### Process Patterns

- Workflow gaps
- Missing steps in procedures
- Communication breakdowns

**Resolution**: Instruction files, checklists, templates

### Technical Patterns

- Recurring bugs
- Performance issues
- Integration failures

**Resolution**: Code fixes, architecture changes, monitoring

### Knowledge Patterns

- Repeated questions
- Undocumented behaviors
- Tribal knowledge gaps

**Resolution**: Documentation, FAQs, glossary entries

---

## Candidate Types

Beyond general patterns, track specific candidate types:

### Glossary Candidates

Terms used 3+ times without definition:

```markdown
"I've noticed [term] has been used several times.
Want me to add a glossary entry for it?"
```

### FAQ Candidates

Questions asked 3+ times:

```markdown
"This question about [topic] has come up 3 times.
Should I add it to an FAQ?"
```

### Instruction Candidates

Procedures explained 3+ times:

```markdown
"I've explained how to [do thing] 3 times now.
Want me to create an instruction file for it?"
```

---

## Examples

### Example 1: First Occurrence

> **During work**: Tests are timing out because they hit the real API.
>
> **Action**: Note it mentally, fix the immediate issue, move on.
>
> **Tracking**: Optional - add to patterns.md if it feels significant.

### Example 2: Second Occurrence

> **During work**: Tests timing out again - same API rate limit issue.
>
> **Action**: Fix it, add to patterns.md tracking.
>
> ```markdown
> ### Test API timeout
> - **Count**: 2
> - **First seen**: 2025-01-15
> - **Last seen**: 2025-01-20
> - **Context**: Integration tests hitting rate limits
> - **Potential fix**: Add API mocking
> ```

### Example 3: Third Occurrence (Threshold)

> **During work**: Another test timeout from API rate limits.
>
> **Action**: Update count to 3, prompt for action:
>
> "I've noticed test timeouts from API rate limits have occurred 3 times now. This seems like a validated pattern. Would you like me to:
>
> 1. Create an instruction file for test API mocking best practices?
> 2. Create an issue to add proper API mocking infrastructure?
> 3. Just note it and continue?"

### Example 4: Pattern Resolution

> **After implementing fix**:
>
> ```markdown
> ## Resolved Patterns
>
> ### Test API timeout
> - **Final count**: 3
> - **Resolution**: Added `tests/mocks/api.ts` with all external API mocks
> - **Date resolved**: 2025-01-22
> - **Prevention**: Instruction added to testing guidelines
> ```

---

## Integration with Retrospectives

During learning loop (retrospective):

1. **Step 4 ("What would you do differently?")** often reveals patterns
2. Check if this insight has appeared before
3. If 3rd+ occurrence, trigger threshold prompt
4. Update patterns.md accordingly

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Learning Loop](./learning_loop.instructions.md) - Pattern discovery during retros
- [Work Logging](./work_logging.instructions.md) - Pattern evidence capture
