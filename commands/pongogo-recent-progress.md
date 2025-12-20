# Project Accomplishment Summary

Generate a summary of recent project progress.

---

## What This Does

1. Reviews recent work:
   - Completed tasks/issues
   - Work log entries
   - Commits

2. Generates progress summary

3. Identifies patterns and themes

---

## Usage

```
/pongogo-recent-progress
```

Or with time range:

```
/pongogo-recent-progress 7d
/pongogo-recent-progress this-week
/pongogo-recent-progress this-month
```

---

## Output

```markdown
# Progress Summary: [Date Range]

## Completed
- Feature X implemented
- Bug Y fixed
- Docs Z updated

## In Progress
- Feature A (70%)
- Investigation B

## Key Decisions
- Chose approach X for reason Y
- Deferred Z until Q1

## Patterns Noticed
- Theme 1 emerging across work
- Recurring challenge with X

## Metrics
- Issues closed: 5
- Commits: 23
- Work log entries: 8
```

---

## Data Sources

Pulls from (if available):
- Work log files (`docs/work-log/` or `wiki/Work-Log-*`)
- Git commit history
- GitHub issues (if PM detected)
- Pattern tracking (`.pongogo/patterns.md`)

---

## Time Ranges

| Option | Meaning |
|--------|--------|
| `1d` | Last 24 hours |
| `7d` | Last 7 days |
| `this-week` | Current week (Mon-Sun) |
| `this-month` | Current month |
| `last-week` | Previous week |

---

## Related

- Work logging: `instructions/_pongogo_core/work_logging.instructions.md`
- Patterns: `instructions/_pongogo_core/pi_tracking.instructions.md`
