# Pongogo Lifecycle Triggers

**Purpose**: Define the automated triggers that drive Pongogo's continuous improvement loop.

**Philosophy**: Conservative thresholds, user approval gates, quiet success, loud failure.

---

## Overview

Pongogo observes patterns in your work and progressively builds institutional knowledge. This happens through a defined lifecycle with clear triggers at each stage.

```
Friction → Detection → Validation → Instruction → Stabilization
    ↑                                                    │
    └────────────── Refinement ←─────────────────────────┘
```

---

## Lifecycle Stages

### 1. Detection

**Trigger**: Same friction pattern observed 3 times

**Action**: Create improvement tracking file in `knowledge/improvements/`

**User Message**:
> "This issue has come up 3 times. I've started tracking it so we can address the root cause."
> → View: `knowledge/improvements/repeated-auth-timeout.md`

**Why 3?** Once is an incident. Twice is coincidence. Three times is a pattern worth addressing.

---

### 2. Validation

**Trigger**: Improvement file has:
- Clear root cause identified
- Proposed solution documented
- No contradicting evidence

**Action**: Mark improvement as VALIDATED

**User Message**:
> "I've identified a clear pattern here: [description]. Ready to create guidance?"

**Validation Criteria**:
- [ ] Root cause is specific (not "things break sometimes")
- [ ] Solution is actionable (not "be more careful")
- [ ] Pattern is generalizable (not one-off situation)

---

### 3. Instruction Creation

**Trigger**: VALIDATED improvement + user approval

**Action**: Generate instruction draft in `knowledge/instructions/`

**User Message**:
> "I've drafted guidance to prevent this in the future. Would you like to review it?"

**What gets created**:
- Instruction file with standard structure
- Cross-reference to original improvement
- Initial routing hints (when to apply)

**User Approval Required**: Yes - we never create instructions without confirmation.

---

### 4. Stabilization

**Trigger**: Instruction routed successfully 5 times without negative feedback

**Action**: Mark instruction as STABLE (internal flag)

**User Message**: None (silent promotion)

**Why silent?** Stable operation shouldn't require celebration. Users notice when things break, not when they work.

---

### 5. Refinement

**Trigger**: User corrects routing 2 times (says "not relevant" or similar)

**Action**: Flag instruction for review

**User Message**:
> "This guidance has been marked as 'not relevant' twice. It may need adjustment. Would you like to review it?"

**Refinement Options**:
- Narrow scope (add exclusion criteria)
- Broaden scope (add inclusion criteria)
- Split into multiple instructions
- Archive if no longer applicable

---

### 6. Deprecation

**Trigger**: Instruction not routed for 30 days

**Action**: Flag as archive candidate

**User Message**:
> "This guidance hasn't been needed in 30 days. Archive it? [Y/n]"

**Deprecation does NOT mean deletion**:
- Archived instructions move to `knowledge/archive/`
- Can be restored if pattern recurs
- Preserves institutional memory

---

## Trigger Summary Table

| Stage | Trigger | Threshold | User Approval | Output |
|-------|---------|-----------|---------------|--------|
| Detection | Same pattern | 3 occurrences | No | Improvement file |
| Validation | Clear root cause | Quality check | No | VALIDATED status |
| Instruction | Validated + approved | N/A | **Yes** | Instruction file |
| Stabilization | Successful routing | 5 routes | No | STABLE flag |
| Refinement | Negative feedback | 2 corrections | No | Review flag |
| Deprecation | No routing | 30 days | **Yes** | Archive candidate |

---

## Design Principles

### 1. Conservative Thresholds
We wait for evidence before acting. Three occurrences, not one. Five successes, not two.

### 2. User Approval Gates
Creating or archiving instructions requires user confirmation. Detection and validation are automatic.

### 3. Negative Feedback Trumps
Even a single strong correction triggers review. We'd rather under-route than over-route.

### 4. Quiet Success, Loud Failure
Don't celebrate normal operation. Alert users when intervention is needed.

### 5. Nothing is Permanent
Instructions can be refined, archived, or restored. The system learns and adapts.

---

## Configuration

Thresholds are configurable in `.pongogo/config.yaml`:

```yaml
lifecycle:
  detection_threshold: 3      # Occurrences before tracking
  stabilization_threshold: 5  # Successful routes before stable
  refinement_threshold: 2     # Corrections before review
  deprecation_days: 30        # Days inactive before archive prompt
```

---

## Related Documentation

- [Seeded Instructions](../seeded-instructions.md) - What ships by default
- [Improvement Tracking](../improvement-tracking.md) - How improvements are structured
- [Instruction Format](../instruction-format.md) - Standard instruction structure
