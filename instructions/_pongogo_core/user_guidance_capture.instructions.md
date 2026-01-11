---
id: core:user_guidance_capture
routing:
  protected: true
  priority: 10
  description: Automatic capture of user preferences and rules
  triggers:
    keywords:
      - always
      - never
      - prefer
      - "don't"
      - remember
      - from_now_on
      - going_forward
      - guidance
      - rule
      - preference
    nlp: "Capture user-expressed rules, preferences, and behavioral guidance"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
---

# User Guidance Capture

**Purpose**: Automatically detect and capture user-expressed rules, preferences, and feedback for future routing.

**Philosophy**: User guidance is implicit knowledge transfer. When captured systematically, it compounds into a personalized knowledge base.

---

## When to Apply

This instruction triggers when:

- Routing response includes a `guidance_action` directive
- User expresses explicit rules ("always do X", "never do Y")
- User states preferences ("I prefer", "I like", "I want")
- User provides correction feedback ("that's wrong because", "actually, you should")
- User establishes patterns ("from now on", "going forward")

---

## Responding to guidance_action

When routing includes a `guidance_action` field, you MUST:

1. **Acknowledge silently**: Do not interrupt user workflow
2. **Capture the guidance**: Log to the project's Potential Improvement (PI) tracking
3. **Continue normally**: Complete the user's primary request

### Example guidance_action Response

```json
{
  "guidance_action": {
    "action": "log_user_guidance",
    "directive": "USER GUIDANCE DETECTED - Capture for future routing",
    "parameters": {
      "content": "Always use TypeScript for new files",
      "guidance_type": "explicit",
      "context": "always use typescript"
    },
    "rationale": "User expressed behavioral rule"
  }
}
```

### How to Capture

1. **Check for existing PI**: Look in `docs/potential_improvements/` or `.pongogo/pi/` for similar guidance
2. **If exists**: Add evidence to the existing PI (increment occurrence count)
3. **If new**: Create a new PI file with type `user_guidance`

### PI Format for User Guidance

```markdown
---
id: PI-XXX
title: "[Brief description of the guidance]"
type: user_guidance
status: TRACKING
occurrence_count: 1
guidance_type: explicit  # or implicit
identified_date: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

# PI-XXX: [Title]

## User Guidance

[The exact guidance expressed by the user]

## Context

[When/why the user expressed this guidance]

## Evidence

- [Date]: [Source/context of occurrence]
```

---

## Core Principles

- **Non-disruptive**: Capture without interrupting user workflow
- **Deduplication**: Similar guidance accumulates as evidence, not duplicates
- **Explicit = Immediate**: Direct user requests are immediately ready for action
- **Implicit = Threshold**: Soft feedback needs 3+ occurrences before surfacing
- **User-controlled**: All promotions require explicit user approval

---

## Guidance Type Behavior

### Explicit Guidance (Direct Requests)

When user explicitly states rules ("always do X", "from now on", "remember this"):

- **Immediate action**: Ready for promotion right away
- **Acknowledge naturally**: "Got it - I'll remember that going forward."
- **Offer to make standard**: "Should I apply this to all future work?"

Example:
> User: "Always run tests before committing"
> Response: "Got it - I'll run tests before every commit going forward."

### Implicit Guidance (Soft Feedback)

When user provides indirect feedback (corrections, preferences expressed in passing):

**After 3+ occurrences** of similar guidance:
- Surface the pattern at a natural breakpoint
- Offer to make it standard (never mention "instruction files")
- Example: "I've noticed you prefer TypeScript for new files. Want me to make this standard?"

**For 1-2 occurrences**:
- Log without interrupting
- Continue tracking

### Correction Signals as Guidance (Routing IMP-018)

correction_signal patterns (84% friction correlation) often contain implicit rules.

**Correction Signal Patterns**:
- "wait, hold on" - User has expectation about pace/process
- "sorry, actually I" - User clarifying preference
- "you're skipping" - User expects step X to happen
- "that's not what I" - User has specific expectation

**Guidance Extraction from Corrections**:

| Correction Signal | Implicit Guidance |
|-------------------|-------------------|
| "you're skipping the tests" | "Always run tests before [action]" |
| "wait, I wanted to review first" | "Let me review before applying changes" |
| "that's not what I meant by done" | "Done means [user's definition]" |
| "we already discussed this" | Previous guidance wasn't captured |

**Processing Correction Signals**:
1. Capture correction as friction event (immediate acknowledgment)
2. Extract implicit guidance from correction content
3. Apply immediately in current session
4. Offer to make extracted guidance standard for future

### User-Focused Language (Required)

When discussing guidance capture with users, always use outcome-focused language:

| Never Say | Say Instead |
|-----------|-------------|
| "Create an instruction file" | "Remember this going forward" |
| "Capture in .pongogo/instructions/" | "Make this standard" |
| "Formalize as an instruction" | "Apply this to future work" |
| "Add to the knowledge base" | "Remember this preference" |

See `_pongogo_collaboration.instructions.md` → "Technical Abstraction" section for complete language guide.

---

## Common Pitfalls

### Pitfall 1: Interrupting User Flow

- **Problem**: Asking about guidance during active work
- **Solution**: Capture silently, surface at session end or natural breaks

### Pitfall 2: Over-capturing

- **Problem**: Treating every statement as guidance
- **Solution**: Focus on explicit rules ("always", "never", "prefer")

### Pitfall 3: Missing Context

- **Problem**: Guidance stored without enough context to be useful
- **Solution**: Always capture the situation that prompted the guidance

---

## Related

- [PI Tracking](./pi_tracking.instructions.md) - Potential Improvement system
- [Learning Loop](./learning_loop.instructions.md) - Capturing learnings
- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
