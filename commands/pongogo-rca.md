# Start RCA Wizard

Conduct a Root Cause Analysis for incidents or failures.

---

## What This Does

1. Guides through RCA process:
   - What happened?
   - Timeline of events
   - 5 Whys analysis
   - Root cause identification
   - Corrective actions

2. Creates RCA document

3. Tracks follow-up actions

---

## Usage

```
/pongogo-rca
```

Or with incident description:

```
/pongogo-rca "production outage at 3pm"
```

---

## RCA Template

### 1. Incident Summary
- What happened?
- When did it happen?
- Who was affected?
- How was it detected?

### 2. Timeline
- First sign of issue
- Key events
- Resolution time

### 3. 5 Whys Analysis
1. Why did [symptom] happen?
2. Why did [cause 1] happen?
3. Why did [cause 2] happen?
4. Why did [cause 3] happen?
5. Why did [root cause] exist?

### 4. Root Cause
The fundamental reason the incident occurred.

### 5. Corrective Actions
- Immediate: What fixed it now?
- Short-term: What prevents recurrence?
- Long-term: What systemic change needed?

---

## Output

Creates RCA document:

```markdown
# RCA: [Incident Title]

**Date**: YYYY-MM-DD
**Severity**: High/Medium/Low
**Status**: Open/Resolved

## Summary
...

## Root Cause
...

## Corrective Actions
- [ ] Action 1 (owner, due date)
- [ ] Action 2 (owner, due date)
```

---

## Related

- Triggers: Pattern tracking if similar incidents recur
- Follow-up: Tracks corrective action completion
