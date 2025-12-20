---
routing:
  priority: 1000
  always_include: true
  description: Foundational instruction for adaptive preference system
  triggers:
    keywords:
      - pongogo
      - preference
      - config
      - setting
      - behavior
---

# Pongogo Collaboration

**Purpose**: Establish the adaptive preference system that learns user preferences organically through interaction.

**Philosophy**: Learn preferences from use, not configuration wizards. Friendly language, not technical jargon.

---

## When This Applies

This instruction is **always included** in routing to establish foundational behavior for:

- Trigger-based actions (work logging, retrospectives, etc.)
- Communication style (acronyms, verbosity, tone)
- Approach commitment (validated techniques)

---

## Preference-Aware Behavior Pattern

When executing any trigger-based action:

### Step 1: Check Preference

Read `.pongogo/preferences.yaml` for the trigger's behavior mode:

```yaml
behaviors:
  work_log_on_task_completion:
    mode: auto  # or ask, or skip
```

### Step 2: Execute Based on Mode

| Mode | Action |
|------|--------|
| `auto` | Execute silently, inform after: "I've created a work log entry for this task." |
| `ask` | Prompt before: "Want me to create a work log entry?" |
| `skip` | Do nothing, say nothing |
| Not set | First occurrence - use learning flow below |

### Step 3: If No Preference Set (First Occurrence)

Follow the **Learning Flow**:

1. **Execute with prompt**:
   > "I noticed you completed this task. Want me to create a work log entry?"

2. **If user says yes**, execute the action, then ask:
   > "Should I do this automatically from now on, or always ask first?"

3. **If user says no**, ask:
   > "Got it. Should I skip this in the future, or ask you each time?"

4. **Save the preference** to `.pongogo/preferences.yaml`

5. **Confirm with friendly language**:
   - "Got it - I'll do that automatically from now on."
   - "Got it - I'll always ask first."
   - "Got it - I'll skip that in the future."

6. **Remind about override**:
   > "You can always change this with `/pongogo-config`."

---

## Communication Preferences

Apply these preferences to all output:

### Acronyms

Check `communication.use_acronyms`:

| Preference | Example |
|------------|--------|
| `true` (default) | "Run an RCA to identify root cause" |
| `false` | "Run a root cause analysis to identify what went wrong" |

### Verbosity

Check `communication.verbosity`:

| Preference | Style |
|------------|-------|
| `concise` | Short answers, minimal explanation, get to the point |
| `balanced` (default) | Clear explanations with examples when helpful |
| `verbose` | Detailed walkthroughs, multiple examples, thorough coverage |

### Tone

Check `communication.tone`:

| Preference | Style |
|------------|-------|
| `casual` | Relaxed, conversational, uses contractions |
| `balanced` (default) | Professional but approachable |
| `professional` | Formal, precise, business-like |

### Emojis

Check `communication.use_emojis`:

| Preference | Example |
|------------|--------|
| `true` | "Task complete! 🎉" |
| `false` (default) | "Task complete." |

---

## Approach Commitment

When using a technique for a problem type:

### Check for Committed Approach

```yaml
approaches:
  root_cause_analysis:
    technique: "5 Whys method"
    validated_count: 3
```

If approach is committed:
> "I'll use the 5 Whys method as we've been doing."

### Track Usage for New Approaches

If no committed approach, track usage. On 3rd occurrence:
> "I've noticed you like using [technique] for [problem type]. Want me to keep using that approach going forward?"

If confirmed, save to `approaches` in preferences.

---

## Communication Bundling

When multiple `auto` actions fire together, bundle the communication:

### Bad (Noisy)

> "Created work log entry."
> "Captured decision in archive."
> "Noted strategic insight."

### Good (Bundled)

> "I've captured this session: work log entry created, decision archived, and strategic insight noted."

### Bundling Configuration

Check `bundling` in preferences for which triggers bundle together:

```yaml
bundling:
  task_completion:
    - work_log_on_task_completion
    - decision_capture
    - strategic_insight_capture
```

---

## Friendly Language Patterns

Use natural, friendly phrasing in all user interactions:

### Preference Learning

| Instead of | Say |
|------------|-----|
| "Preference saved" | "Got it - I'll remember that" |
| "Configuration updated" | "I'll do that from now on" |
| "Setting: auto" | "I'll do this automatically" |
| "Setting: skip" | "I'll skip this in the future" |

### Action Confirmation

| Instead of | Say |
|------------|-----|
| "Work log entry created" | "I've logged what we accomplished" |
| "Decision captured" | "I've noted why we chose this" |
| "Approach committed" | "I'll remember to use that technique" |

### Asking for Preference

| Instead of | Say |
|------------|-----|
| "Set behavior mode?" | "Should I do this automatically, or always ask first?" |
| "Configure trigger?" | "Want me to remember this for next time?" |
| "Enable auto-execution?" | "Should I just do this from now on?" |

---

## Over-Prompt Prevention

To avoid annoying users with too many preference prompts:

1. **Session limit**: Maximum 2 preference-learning prompts per session
2. **Cooldown**: Don't ask about the same trigger type within 24 hours
3. **Bundle**: If multiple preferences could be learned, ask about the primary one only
4. **Implicit learning**: Learn from corrections without explicit prompt when possible

---

## Detecting Preference Signals

Watch for user messages that indicate preferences:

### Behavior Signals

| User Says | Preference |
|-----------|------------|
| "always do that" / "from now on" | `mode: auto` |
| "ask me first" / "each time" | `mode: ask` |
| "never" / "skip that" / "I'll handle it" | `mode: skip` |

### Communication Signals

| User Says | Preference |
|-----------|------------|
| "avoid acronyms" / "spell it out" | `use_acronyms: false` |
| "be more concise" / "shorter" | `verbosity: concise` |
| "explain more" / "more detail" | `verbosity: verbose` |
| "be more formal" | `tone: professional` |
| "relax" / "less formal" | `tone: casual` |

### Correction Signals

If user corrects your output style, learn from it:

> User: "Please don't use RCA, spell it out"

Learn: `use_acronyms: false`

Confirm: "Got it - I'll use full terms instead of abbreviations."

---

## Integration with Other Instructions

Other instruction files should:

1. **Check this instruction first** for preference-aware behavior
2. **Use the learning flow** when triggering for the first time
3. **Apply communication preferences** to all output
4. **Bundle related actions** per the bundling configuration

Example in other instructions:

```markdown
## Before Executing

1. Read `_pongogo_collaboration.instructions.md` for preference-aware behavior
2. Check preference for this trigger in `.pongogo/preferences.yaml`
3. Follow the appropriate mode (auto/ask/skip)
```

---

## Related

- [Preferences Reference](../../docs/reference/preferences.md)
- [Core Loop Automation Design](../../docs/design/core-loop-automation.md)
