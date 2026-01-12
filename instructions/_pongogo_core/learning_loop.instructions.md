---
id: core:learning_loop
routing:
  protected: true
  priority: 10
  description: Simple retrospective for learning capture
  triggers:
    keywords:
      - learning_loop
      - retrospective
      - retro
      - what_worked
      - what_we_learned
      - lessons_learned
      - completed_work
      - task_done
      - done
      - finished
      - shipped
      - completed
      - wrapped_up
    nlp: "Conduct retrospective to capture learnings from completed work"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
evaluation:
  success_signals:
    - All 4 questions answered with specific details
    - Learnings are actionable (not vague)
    - Patterns tracked when recurring
    - Retrospective depth matches work complexity
  failure_signals:
    - Generic answers without specifics
    - Skipped retrospective due to time pressure
    - Learnings not captured before moving on
    - Same issues recur without pattern recognition
---

# Learning Loop

**Purpose**: Capture learnings from completed work through a simple 4-question retrospective.

**Philosophy**: Every piece of completed work contains lessons. Capture them before moving on.

---

## When to Apply

This instruction triggers when:

- Task, feature, or significant work unit is complete
- User says "done", "finished", "completed", "shipped"
- Before closing an issue or moving to next work
- When patterns or insights emerged during work
- **Friction events** - User corrections, frustration, or repeated issues (see below)

---

## Preference-Aware Behavior

**Before executing**, check `.pongogo/preferences.yaml`:

```yaml
behaviors:
  retro_on_task_completion:
    mode: auto | ask | skip
```

Follow the behavior mode per `_pongogo_collaboration.instructions.md`.

---

## Learning Loop Workflow

<learning-workflow>
<step number="1" action="assess-depth">
Determine retrospective depth: quick (routine task), standard (significant feature), deep (milestone/incident).
</step>

<step number="2" action="answer-questions">
Work through the 4 questions below. Be specific, not generic.
</step>

<step number="3" action="check-patterns">
Is this insight recurring? Track if 1st/2nd occurrence; promote if 3rd+.
</step>

<step number="4" action="document">
Record in appropriate location (work log, issue comment, or dedicated doc).
</step>

<gate>Do not skip retrospective. Every completed work has learnings. Capture before moving on.</gate>
</learning-workflow>

---

## The 4 Questions

<retrospective-questions>
<question id="accomplished" sequence="1">
<prompt>What was accomplished?</prompt>
<guidance>Brief summary of deliverables</guidance>
<sub-prompts>
<item>What was built, fixed, or changed?</item>
<item>What's the user-visible outcome?</item>
<item>What files/components were affected?</item>
</sub-prompts>
<quality-check>Answer should be specific enough that someone else could verify the work was done</quality-check>
</question>

<question id="worked-well" sequence="2">
<prompt>What worked well?</prompt>
<guidance>Identify successful approaches worth repeating</guidance>
<sub-prompts>
<item>What techniques were effective?</item>
<item>What decisions paid off?</item>
<item>What would you do again?</item>
</sub-prompts>
<quality-check>Answers should be reusable insights, not just "it worked"</quality-check>
</question>

<question id="challenging" sequence="3">
<prompt>What was challenging?</prompt>
<guidance>Capture obstacles and how they were overcome</guidance>
<sub-prompts>
<item>What blockers were encountered?</item>
<item>What took longer than expected?</item>
<item>What required iteration?</item>
</sub-prompts>
<quality-check>Include how challenges were resolved, not just what was hard</quality-check>
</question>

<question id="differently" sequence="4">
<prompt>What would you do differently?</prompt>
<guidance>Extract actionable learnings for future work</guidance>
<sub-prompts>
<item>What insight emerged?</item>
<item>What approach would be better next time?</item>
<item>What pattern should be remembered?</item>
</sub-prompts>
<quality-check>Learnings should be actionable, not vague ("plan better" is too vague)</quality-check>
</question>
</retrospective-questions>

---

## Output Format

### Simple Format (default)

```markdown
## Retrospective: [Work Title]

**Accomplished**: Brief summary of what was done

**Worked Well**: What techniques/approaches succeeded

**Challenging**: What obstacles were overcome

**Next Time**: What to do differently
```

### With Evidence (optional)

```markdown
## Retrospective: [Work Title]

**Date**: YYYY-MM-DD
**Duration**: X hours/days

**Accomplished**:
- Deliverable 1
- Deliverable 2

**Worked Well**:
- Approach that succeeded
- Decision that paid off

**Challenging**:
- Blocker and how it was resolved
- Unexpected complexity

**Next Time**:
- Insight to remember
- Better approach for future

**Evidence**:
- Commits: [links]
- Files: [list]
```

---

## Pattern Detection

During the retrospective, watch for patterns:

**If the same insight appears 3+ times** across different work:
- This is a validated pattern
- Offer to make it a standard process going forward
- See `pi_tracking.instructions.md` for threshold tracking

**If this is the 1st or 2nd occurrence**:
- Note it for future reference
- Track in pattern candidates if using PI system

---

## Friction-Triggered Learning (Routing IMP-018)

Friction events are learning opportunities that shouldn't wait until task completion.

### Friction Trigger Signals

When you detect these signals, conduct a mini-retro immediately:

- User expresses frustration ("yet another example of", "we already discussed")
- Repeated corrections on same issue
- "i thought we changed/fixed this"
- "without going through process"

### Mini-Retro for Friction (2 questions)

Don't wait for task completion - capture friction learning while context is fresh:

**1. What caused the friction?**
- What did the user expect vs what happened?
- Was this a misunderstanding, process gap, or repeated issue?

**2. How can we prevent this category in the future?**
- Is this a one-time issue or pattern?
- What systematic change would prevent recurrence?

### Why Capture Immediately

- Friction context is freshest right after the event
- Waiting until task completion may lose important details
- Prevents same friction from recurring in current session
- Friction often signals a systematic gap (valuable learning)

### Example Friction Mini-Retro

> **Friction**: User said "you're skipping the verification step again"
>
> **What caused it**: Completed work without showing user for approval before proceeding
>
> **Prevention**: Add verification checkpoint before significant actions. User prefers: "always show me before applying changes"
>
> **Pattern?**: 2nd occurrence. If happens again, make this standard process.

---

## Depth Levels

### Level 1: Quick Retro (5-10 min)

For routine tasks:
- 4 questions, brief answers
- Capture in work log or issue comment
- Move on quickly

### Level 2: Standard Retro (15-30 min)

For significant features or multi-day work:
- 4 questions with examples
- Document patterns discovered
- Update relevant docs if needed

### Level 3: Deep Retro (1+ hour)

For major milestones or after incidents:
- Comprehensive 4 questions
- Root cause analysis if failure occurred
- Institutionalize learnings as standard processes
- Update documentation and patterns

---

## Integration with Work Log

If `work_log_on_task_completion` preference is `auto`:
- Bundle retrospective with work log entry
- Include retrospective summary in work log
- Single communication: "I've logged what we accomplished and captured the learnings."

---

## Handling Uncertainty

<uncertainty-protocol>
If unable to answer a question:

1. **State what's unclear** - "I don't have visibility into [X] to answer this question"
2. **Ask user** - "What challenges did you encounter that I might have missed?"
3. **Don't fabricate** - Better to have incomplete retrospective than invented learnings

<when-answers-unclear>
- "What worked well?" - If I only executed steps, I may not know what was innovative. Ask user.
- "What was challenging?" - User may have struggled with aspects I didn't see.
- "What would you do differently?" - User perspective is essential for this question.
</when-answers-unclear>

<acceptable-responses>
- "From my perspective, [X] worked well. Did you find other approaches effective?"
- "I observed challenges with [X]. Were there other obstacles I might have missed?"
- "I'm not sure what would be done differently. What's your take on that?"
</acceptable-responses>

<unacceptable-responses>
- Inventing learnings not supported by actual work
- Generic platitudes ("communication is important")
- Skipping questions because answers are hard
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="specific-not-generic">Every answer must reference specific work done. "Testing helped" is bad; "Testing the auth flow in isolation caught the token refresh bug" is good.</rule>
<rule id="verify-accomplishments">Only list accomplishments that can be verified (commits, files changed, issues closed). Don't claim work not done.</rule>
<rule id="actionable-learnings">Learnings must be actionable. If you can't describe how to apply it next time, it's not actionable.</rule>
<rule id="pattern-tracking-honest">Track patterns honestly. If you're unsure if something is recurring, check history first.</rule>
</grounding>

---

## Examples

### Example 1: Quick Retro

> **Accomplished**: Fixed login timeout bug by increasing session duration
>
> **Worked Well**: Using browser dev tools to trace the issue quickly
>
> **Challenging**: Understanding the session middleware layering
>
> **Next Time**: Add session duration to config file for easier adjustment

### Example 2: Standard Retro

> ## Retrospective: User Authentication Refactor
>
> **Accomplished**:
> - Migrated from session-based to JWT auth
> - Added refresh token rotation
> - Updated 12 API endpoints
>
> **Worked Well**:
> - Testing each endpoint in isolation before integration
> - Creating a migration script for existing sessions
>
> **Challenging**:
> - Token refresh timing with concurrent requests
> - Backwards compatibility for mobile app
>
> **Next Time**:
> - Design token refresh strategy upfront
> - Create compatibility layer earlier in the process

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [Work Logging](./work_logging.instructions.md) - Capturing work progress
- [PI Tracking](./pi_tracking.instructions.md) - Pattern threshold detection
