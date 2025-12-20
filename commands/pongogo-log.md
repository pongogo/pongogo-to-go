# Create Work Log Entry

Add an entry to the work log tracking progress and decisions.

---

## What This Does

1. Prompts for entry type and content
2. Creates formatted work log entry
3. Adds to appropriate log file
4. Optionally commits the change

---

## Usage

```
/pongogo-log
```

Or with type:

```
/pongogo-log task
/pongogo-log decision
/pongogo-log blocker
```

---

## Entry Types

| Type | Use For |
|------|--------|
| `task` | Completing a task or feature |
| `decision` | Key architectural or design choice |
| `blocker` | Obstacle encountered or resolved |
| `learning` | Insight or pattern discovered |
| `session` | End-of-session summary |

---

## Output

Creates entry in work log:

```markdown
### [TIME] [TYPE] - Brief Title

Description of what was done.

**Key Decision**: [If applicable]
**Next Step**: [What comes next]
```

---

## Work Log Location

Entries are added to (in order of preference):
1. `wiki/Work-Log-YYYY-MM.md`
2. `docs/work-log/YYYY-MM.md`
3. Relevant GitHub issue comment

---

## Related

- Instruction: `instructions/_pongogo_core/work_logging.instructions.md`
- Bundled with: `/pongogo-retro` (if preference set)
