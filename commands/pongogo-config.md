# Edit Preferences

View or modify Pongogo preferences.

---

## What This Does

1. Shows current preferences
2. Allows editing behavior and communication settings
3. Saves changes to `.pongogo/preferences.yaml`

---

## Usage

```
/pongogo-config
```

Or with specific action:

```
/pongogo-config show
/pongogo-config edit
/pongogo-config reset
```

---

## Preference Categories

### Behavior Preferences

How proactive Pongogo is for each trigger:

| Mode | Meaning |
|------|--------|
| `auto` | Just do it, inform after |
| `ask` | Prompt before doing |
| `skip` | Don't do or mention |

Example triggers:
- `work_log_on_task_completion`
- `retro_on_epic_completion`
- `decision_capture`

### Communication Preferences

How Pongogo communicates:

| Setting | Options |
|---------|--------|
| `use_acronyms` | true / false |
| `verbosity` | concise / balanced / verbose |
| `tone` | casual / balanced / professional |
| `use_emojis` | true / false |

### Approach Commitments

Validated techniques Pongogo remembers:

```yaml
approaches:
  root_cause_analysis:
    technique: "5 Whys method"
```

---

## Commands

### Show Preferences

```
/pongogo-config show
```

Displays current preferences in readable format.

### Edit Preferences

```
/pongogo-config edit work_log_on_task_completion auto
/pongogo-config edit verbosity concise
/pongogo-config edit use_acronyms false
```

### Reset Preferences

```
/pongogo-config reset
```

Resets all preferences to defaults (requires confirmation).

---

## File Location

Preferences are stored in:

```
.pongogo/preferences.yaml
```

You can also edit this file directly.

---

## Related

- Reference: `docs/reference/preferences.md`
- Foundational: `instructions/_pongogo_core/_pongogo_collaboration.instructions.md`
