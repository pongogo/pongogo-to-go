---
routing:
  priority: 15
  description: Handle incidents, bugs, and failures with RCA
  triggers:
    keywords:
      - bug
      - broken
      - failed
      - failing
      - error
      - incident
      - outage
      - crash
      - not_working
      - regression
    nlp: "Investigate and resolve bugs, failures, or incidents"
  includes:
    - _pongogo_core/_pongogo_collaboration.instructions.md
---

# Incident Handling

**Purpose**: Guide response to bugs, failures, and incidents with structured RCA.

**Philosophy**: Every incident is a learning opportunity. Fix it, understand it, prevent it.

---

## When to Apply

This instruction triggers when:

- User reports a bug or failure
- Error messages or stack traces appear
- Something that worked before is now broken
- Tests are failing unexpectedly
- Production issue or outage

---

## Preference-Aware Behavior

**Before executing**, check `.pongogo/preferences.yaml`:

```yaml
behaviors:
  rca_on_incident:
    mode: auto | ask | skip
```

Follow the behavior mode per `_pongogo_collaboration.instructions.md`.

---

## Response Flow

### 1. Acknowledge & Assess

```
"I see there's an issue with [X]. Let me investigate."
```

Quick assessment:
- **Severity**: Critical / High / Medium / Low
- **Scope**: Single user / Feature / System-wide
- **Urgency**: Blocking / Inconvenient / Minor

### 2. Investigate

- Reproduce the issue if possible
- Check recent changes (commits, deploys)
- Review error logs/stack traces
- Identify affected components

### 3. Fix

- Implement targeted fix
- Test the fix
- Verify original issue resolved
- Check for side effects

### 4. Document

- Brief RCA (see format below)
- Work log entry
- Update issue if applicable

---

## Simple RCA Format

```markdown
## RCA: [Brief Title]

**Date**: YYYY-MM-DD
**Severity**: Critical / High / Medium / Low

### What Happened

Brief description of the incident.

### Root Cause

Why it happened (not just what broke).

### Fix Applied

What was done to resolve it.

### Prevention

What will prevent recurrence:
- [ ] Action item 1
- [ ] Action item 2

### Timeline

- HH:MM - Issue reported
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Verified resolved
```

---

## 5 Whys Method

For complex issues, use 5 Whys to find root cause:

```
Why 1: Why did the test fail?
  → The API returned 500

Why 2: Why did the API return 500?
  → Database connection timed out

Why 3: Why did the connection time out?
  → Connection pool exhausted

Why 4: Why was the pool exhausted?
  → Connections not being released

Why 5: Why weren't connections released?
  → Missing finally block in query wrapper

Root Cause: Query wrapper doesn't release connections on error
Fix: Add proper connection release in finally block
```

---

## Severity Guidelines

| Severity | Impact | Examples |
|----------|--------|----------|
| **Critical** | System down, data loss | Production outage, data corruption |
| **High** | Major feature broken | Login broken, payments failing |
| **Medium** | Feature degraded | Slow performance, partial failure |
| **Low** | Minor inconvenience | UI glitch, non-blocking error |

---

## Pattern Detection

During RCA, check if this is a recurring pattern:

**If similar issue occurred before**:
- Note occurrence count
- On 3rd occurrence, suggest systemic fix
- See `pi_tracking.instructions.md`

**Questions to ask**:
- Has this component failed before?
- Is this a category of issue we've seen?
- What pattern does this fit?

---

## Examples

### Example 1: Quick Bug Fix

```markdown
## RCA: Login redirect loop

**Date**: 2025-01-20
**Severity**: High

### What Happened

Users stuck in redirect loop after login.

### Root Cause

Session cookie domain mismatch after DNS change.

### Fix Applied

Updated cookie domain in auth config.

### Prevention

- [ ] Add cookie domain to deploy checklist
```

### Example 2: Complex Incident

```markdown
## RCA: Database connection exhaustion

**Date**: 2025-01-20
**Severity**: Critical

### What Happened

API returning 500 errors, all requests failing.

### Root Cause (5 Whys)

1. API returning 500 → Database queries timing out
2. Queries timing out → No available connections
3. No connections → Pool exhausted (100/100 in use)
4. Pool exhausted → Connections not released
5. Not released → Missing error handling in query wrapper

### Fix Applied

- Added try/finally to ensure connection release
- Increased pool size from 100 to 200 temporarily
- Added connection monitoring

### Prevention

- [ ] Add connection pool alerting (> 80% used)
- [ ] Code review for connection handling patterns
- [ ] Add integration test for connection release

### Timeline

- 14:30 - Alerts fired, investigation started
- 14:45 - Identified connection pool issue
- 15:00 - Deployed hotfix
- 15:10 - Verified resolved, monitoring
```

---

## Integration with Other Instructions

### After Incident Resolved

1. **Work log entry**: Document in work log
2. **Pattern check**: Is this 3rd+ occurrence?
3. **Retrospective**: For high/critical incidents

### Bundling

If configured for auto:
```
"I've fixed the issue, documented the RCA, and added it to the work log."
```

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [PI Tracking](./pi_tracking.instructions.md) - Pattern detection
- [Work Logging](./work_logging.instructions.md) - Incident documentation
- [Learning Loop](./learning_loop.instructions.md) - Post-incident retrospective
