# Preferences Reference

Pongogo learns user preferences organically through interaction. This document describes all preference keys and their effects.

## File Location

```
.pongogo/preferences.yaml
```

This file is auto-generated on first preference learned. Edit via `/pongogo-config` or manually.

---

## Behavior Preferences

Control how proactive Pongogo is for each trigger.

### Modes

| Mode | Behavior | Example |
|------|----------|--------|
| `auto` | Execute silently, inform after | "Created work log entry for Task X" |
| `ask` | Prompt before executing | "Want me to create a work log entry?" |
| `skip` | Don't execute or mention | Silent |

### Trigger Keys

#### Work Completion

| Key | Description | Default |
|-----|-------------|--------|
| `work_log_on_task_completion` | Create work log entry when task finishes | `ask` |
| `retro_on_epic_completion` | Conduct L2 retrospective when epic closes | `ask` |
| `retro_on_milestone_completion` | Conduct L3 retrospective when milestone closes | `ask` |

#### Learning Capture

| Key | Description | Default |
|-----|-------------|--------|
| `rca_on_incident` | Start RCA when incident detected | `ask` |
| `rca_followup_tracking` | Track RCA follow-up actions | `auto` |

#### PI System

| Key | Description | Default |
|-----|-------------|--------|
| `pi_threshold_prompt` | Suggest instruction creation at 3+ occurrences | `ask` |

#### Knowledge Institutionalization

| Key | Description | Default |
|-----|-------------|--------|
| `decision_capture` | Capture architectural decisions | `auto` |
| `strategic_insight_capture` | Note strategic insights | `auto` |
| `approach_commitment` | Commit validated approaches | `ask` |
| `glossary_candidate` | Suggest glossary entry at 3+ uses | `ask` |
| `faq_candidate` | Suggest FAQ entry at 3+ questions | `ask` |

#### Issue Lifecycle (GitHub PM)

These only activate if GitHub PM is detected during `pongogo init`.

| Key | Description | Default |
|-----|-------------|--------|
| `issue_template_apply` | Apply template to new issues | `ask` |
| `issue_status_verify` | Verify prerequisites on status change | `ask` |
| `issue_completion_comment` | Add completion comment | `ask` |
| `issue_closure` | Final closure actions | `ask` |

### Example

```yaml
behaviors:
  work_log_on_task_completion:
    mode: auto
    learned_at: 2025-12-20T14:30:00Z
    learned_from: "User said 'yes, always do that'"

  retro_on_epic_completion:
    mode: ask
    learned_at: 2025-12-20T15:00:00Z
```

---

## Communication Preferences

Control how Pongogo communicates.

### Keys

| Key | Values | Default | Description |
|-----|--------|---------|-------------|
| `use_acronyms` | `true` / `false` | `true` | Use abbreviations like "RCA" vs "Root Cause Analysis" |
| `verbosity` | `concise` / `balanced` / `verbose` | `balanced` | How detailed explanations should be |
| `tone` | `casual` / `balanced` / `professional` | `balanced` | Communication style |
| `use_emojis` | `true` / `false` | `false` | Include emojis in responses |

### Example

```yaml
communication:
  use_acronyms: false
  use_acronyms_learned_at: 2025-12-20T16:00:00Z
  use_acronyms_learned_from: "User said 'please avoid acronyms'"

  verbosity: concise
  verbosity_learned_at: 2025-12-21T08:00:00Z

  tone: professional
  use_emojis: false
```

---

## Approach Commitments

Validated techniques Pongogo remembers to use for specific problem types.

### Structure

```yaml
approaches:
  <problem_type>:
    technique: "Description of the technique"
    validated_count: 3
    committed_at: 2025-12-20T14:00:00Z
    committed_from: "User confirmed after 3rd use"
```

### Common Problem Types

| Type | Example Techniques |
|------|-------------------|
| `root_cause_analysis` | "5 Whys method", "Fishbone diagram" |
| `debugging` | "Reproduce first, then investigate" |
| `code_review` | "Security-first checklist" |
| `design` | "Start with user stories" |
| `estimation` | "Break into 2-hour chunks" |

### Example

```yaml
approaches:
  root_cause_analysis:
    technique: "5 Whys method"
    validated_count: 5
    committed_at: 2025-12-20T14:00:00Z
    committed_from: "User confirmed after 3rd use"

  debugging:
    technique: "Reproduce first, then investigate"
    validated_count: 4
    committed_at: 2025-12-19T16:00:00Z
```

---

## Action Bundling

When multiple triggers fire together, bundle the communication.

### Structure

```yaml
bundling:
  <event>:
    - trigger_key_1
    - trigger_key_2
```

### Defaults

```yaml
bundling:
  task_completion:
    - work_log_on_task_completion
    - decision_capture
    - strategic_insight_capture

  epic_completion:
    - retro_on_epic_completion
    - work_log_on_task_completion
```

### Effect

**Without bundling** (noisy):
> "Created work log entry."
> "Captured decision in archive."
> "Noted strategic insight."

**With bundling** (clean):
> "I've captured this session: work log entry created, decision archived, and strategic insight noted."

---

## Learning Flow

### First Occurrence

1. Trigger detected (e.g., task completion)
2. Pongogo prompts: "I noticed you completed this task. Want me to create a work log entry?"
3. User responds (yes/no)
4. Pongogo asks: "Should I do this automatically from now on, or always ask first?"
5. Preference saved to `.pongogo/preferences.yaml`

### Subsequent Occurrences

Behavior follows saved preference:
- `auto`: Execute silently, inform after
- `ask`: Prompt before
- `skip`: Do nothing

### Override

User can always change preferences via `/pongogo-config`.

---

## Full Example

```yaml
# Pongogo Preferences
# Auto-generated through use - edit via /pongogo-config

version: 1
learned_at: 2025-12-20T12:00:00Z

behaviors:
  work_log_on_task_completion:
    mode: auto
    learned_at: 2025-12-20T14:30:00Z
    learned_from: "User said 'yes, always do that'"

  retro_on_epic_completion:
    mode: ask
    learned_at: 2025-12-20T15:00:00Z

  decision_capture:
    mode: auto
    learned_at: 2025-12-22T09:00:00Z

communication:
  use_acronyms: false
  use_acronyms_learned_at: 2025-12-20T16:00:00Z
  use_acronyms_learned_from: "User said 'please avoid acronyms'"

  verbosity: concise
  verbosity_learned_at: 2025-12-21T08:00:00Z

  tone: professional
  use_emojis: false

approaches:
  root_cause_analysis:
    technique: "5 Whys method"
    validated_count: 5
    committed_at: 2025-12-20T14:00:00Z

bundling:
  task_completion:
    - work_log_on_task_completion
    - decision_capture
    - strategic_insight_capture
```

---

## Python API

```python
from pathlib import Path
from pongogo.cli.preferences import (
    load_preferences,
    get_behavior_mode,
    set_behavior_mode,
    get_communication_preference,
    set_communication_preference,
    get_approach,
    commit_approach,
)

project_root = Path(".")

# Load preferences
prefs = load_preferences(project_root)

# Check behavior mode
mode = get_behavior_mode(prefs, "work_log_on_task_completion")
if mode == "auto":
    # Execute silently
    pass
elif mode == "ask":
    # Prompt first
    pass
elif mode is None:
    # First time - prompt and learn
    set_behavior_mode(project_root, "work_log_on_task_completion", "auto",
                      learned_from="User said 'yes, always'")

# Check communication preferences
if not prefs.get("communication", {}).get("use_acronyms", True):
    # Spell out acronyms
    pass

# Get committed approach
approach = get_approach(prefs, "root_cause_analysis")
if approach:
    print(f"Using {approach['technique']} as we discussed")
```
