---
id: core:incident_handling
routing:
  protected: true
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
evaluation:
  success_signals:
    - Root cause identified (not just symptoms)
    - Fix addresses root cause, not just symptom
    - Prevention actions documented
    - RCA template completed with real details
  failure_signals:
    - Fix applied without understanding cause
    - RCA skipped for time pressure
    - Same incident recurs without pattern tracking
    - Prevention actions not actionable
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

<incident-response-flow>
<step number="1" action="acknowledge-assess">
<description>Acknowledge issue and assess severity</description>
<output>"I see there's an issue with [X]. Let me investigate."</output>
<assessment>
<dimension id="severity">Critical / High / Medium / Low</dimension>
<dimension id="scope">Single user / Feature / System-wide</dimension>
<dimension id="urgency">Blocking / Inconvenient / Minor</dimension>
</assessment>
<gate>For Critical severity, communicate urgency before deep investigation</gate>
</step>

<step number="2" action="investigate">
<description>Find root cause, not just symptoms</description>
<actions>
<action required="true">Reproduce the issue if possible</action>
<action required="true">Check recent changes (commits, deploys)</action>
<action required="true">Review error logs/stack traces</action>
<action required="true">Identify affected components</action>
<action required="conditional">Use 5 Whys for complex issues</action>
</actions>
<gate>Do not skip to fix without understanding cause. "Fix first, understand later" creates repeat incidents.</gate>
</step>

<step number="3" action="fix">
<description>Implement targeted fix addressing root cause</description>
<actions>
<action required="true">Implement fix that addresses root cause</action>
<action required="true">Test the fix</action>
<action required="true">Verify original issue resolved</action>
<action required="true">Check for side effects</action>
</actions>
<gate>Verify fix addresses ROOT cause, not just symptom</gate>
</step>

<step number="4" action="document">
<description>Create RCA and capture learning</description>
<actions>
<action required="true">Complete RCA template (see below)</action>
<action required="true">Add work log entry</action>
<action required="conditional">Update issue if applicable</action>
<action required="true">Document prevention actions</action>
</actions>
<gate>RCA is not optional. Every incident is a learning opportunity.</gate>
</step>
</incident-response-flow>

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

<severity-definitions>
<severity id="critical" priority="1">
<impact>System down, data loss possible</impact>
<examples>Production outage, data corruption, security breach</examples>
<response-time>Immediate - drop everything</response-time>
<escalation>Notify stakeholders immediately</escalation>
</severity>

<severity id="high" priority="2">
<impact>Major feature broken</impact>
<examples>Login broken, payments failing, core workflow blocked</examples>
<response-time>Within hours</response-time>
<escalation>Notify team lead if not resolved quickly</escalation>
</severity>

<severity id="medium" priority="3">
<impact>Feature degraded but workaround exists</impact>
<examples>Slow performance, partial failure, error messages</examples>
<response-time>Within 24 hours</response-time>
<escalation>Document and prioritize in next sprint</escalation>
</severity>

<severity id="low" priority="4">
<impact>Minor inconvenience</impact>
<examples>UI glitch, non-blocking error, cosmetic issue</examples>
<response-time>When capacity available</response-time>
<escalation>Add to backlog</escalation>
</severity>
</severity-definitions>

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

## Handling Uncertainty

<uncertainty-protocol>
If root cause cannot be determined:

1. **State explicitly** - "I cannot determine the root cause because [reason]"
2. **Document what's known** - Symptoms, timeline, attempted investigations
3. **Propose next steps** - What additional information or access is needed
4. **Apply temporary mitigation** - If possible, mitigate while investigating

<when-to-escalate>
- Cannot reproduce issue
- Logs/data insufficient for diagnosis
- Outside area of expertise
- Time-boxed investigation exceeded without progress
</when-to-escalate>

<acceptable-responses>
- "I've investigated for [time] but cannot identify root cause. Here's what I know: [findings]. To continue, I need: [access/data/expertise]."
- "I can apply a workaround to restore functionality while we investigate the underlying cause."
- "This appears to be a [category] issue which may require [expertise]. Should I escalate?"
</acceptable-responses>

<unacceptable-responses>
- Guessing at root cause without evidence
- Applying fix without understanding what it fixes
- Closing incident without RCA because "it works now"
- Skipping documentation due to time pressure
</unacceptable-responses>
</uncertainty-protocol>

---

## Grounding Rules

<grounding>
<rule id="evidence-based">Root cause must be supported by evidence (logs, repro steps, code analysis). No guessing.</rule>
<rule id="fix-matches-cause">Fix must address the identified root cause. Band-aids without understanding cause create repeat incidents.</rule>
<rule id="prevention-is-required">Every RCA must include prevention actions. If we can't prevent recurrence, we haven't learned.</rule>
<rule id="severity-from-impact">Assign severity based on actual impact, not perceived importance. System down = Critical, regardless of feature.</rule>
</grounding>

---

## Related

- [Pongogo Collaboration](./_pongogo_collaboration.instructions.md) - Preference-aware behavior
- [PI Tracking](./pi_tracking.instructions.md) - Pattern detection
- [Work Logging](./work_logging.instructions.md) - Incident documentation
- [Learning Loop](./learning_loop.instructions.md) - Post-incident retrospective
