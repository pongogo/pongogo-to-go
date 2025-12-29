---
description: Edit preferences
---

# Pongogo Config

View and edit Pongogo preferences for trigger behaviors and communication style.

## Usage

```
/pongogo-config                           # View all preferences
/pongogo-config <trigger> <mode>          # Set behavior
/pongogo-config communication <setting> <value>  # Set communication style
/pongogo-config reset                     # Reset all preferences
```

## Behavior Modes

| Mode | Behavior |
|------|----------|
| `auto` | Execute automatically |
| `ask` | Prompt before action |
| `skip` | Don't execute or mention |

## Available Triggers

| Trigger | Description |
|---------|-------------|
| `work_log` | Work log on task completion |
| `retro` | Retrospective on completion |
| `pi_threshold` | PI system threshold prompts |
| `issue_commencement` | Issue start checklist |
| `issue_closure` | Issue completion checklist |
| `rca` | Root cause analysis |
| `decision_capture` | Capture key decisions |

## Examples

```
/pongogo-config work_log auto
/pongogo-config retro ask
/pongogo-config communication verbosity concise
/pongogo-config reset work_log
```

## Output

### View All

```
## Pongogo Preferences

### Behavior Modes

| Trigger | Mode | Learned |
|---------|------|---------|
| work_log | auto | 2025-12-20 |
| retro | ask | 2025-12-20 |

### Communication

| Setting | Value |
|---------|-------|
| Verbosity | balanced |
| Tone | professional |
```

### Set Confirmation

```
Updated: work_log: ask -> auto
```

---

**Location**: `.pongogo/preferences.yaml`
