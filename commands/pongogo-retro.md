# Conduct Learning Loop

Run a retrospective to capture learnings from completed work.

---

## What This Does

1. Asks the 4 retrospective questions:
   - What was accomplished?
   - What worked well?
   - What was challenging?
   - What would you do differently?

2. Captures insights and patterns

3. Optionally creates work log entry (if bundled)

---

## Usage

```
/pongogo-retro
```

Or with context:

```
/pongogo-retro "user authentication refactor"
```

---

## Options

| Option | Description |
|--------|-------------|
| (no args) | Interactive retrospective for recent work |
| `"topic"` | Retrospective focused on specific work |
| `--quick` | Level 1: Brief 5-10 min retro |
| `--deep` | Level 3: Comprehensive 1+ hour retro |

---

## Output

Generates retrospective summary:

```markdown
## Retrospective: [Topic]

**Accomplished**: ...
**Worked Well**: ...
**Challenging**: ...
**Next Time**: ...
```

---

## Related

- Instruction: `instructions/_pongogo_core/learning_loop.instructions.md`
- Bundled with: `/pongogo-log` (if preference set)
