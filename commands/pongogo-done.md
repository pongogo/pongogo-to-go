# Run Completion Checklist

Verify work is complete before closing an issue or marking done.

---

## What This Does

1. Runs through completion checklist:
   - Deliverables complete?
   - Quality verified?
   - Learning captured?
   - Issue updated?

2. Generates completion comment

3. Optionally closes issue (if GitHub PM active)

---

## Usage

```
/pongogo-done
```

Or with issue reference:

```
/pongogo-done #123
```

---

## Checklist

### Deliverables
- [ ] All acceptance criteria met
- [ ] Code changes committed and pushed
- [ ] Tests passing
- [ ] Documentation updated

### Quality
- [ ] No known bugs introduced
- [ ] No breaking changes (or documented)
- [ ] Code reviewed (if required)

### Learning
- [ ] Work log entry created
- [ ] Key decisions documented
- [ ] Patterns noted

### Issue
- [ ] Completion comment added
- [ ] Related issues updated
- [ ] Status moved to Done

---

## Output

Generates completion comment:

```markdown
## Completed

**Summary**: Brief description of what was done

**Deliverables**:
- [x] Item 1
- [x] Item 2

**Evidence**: Commits, tests, docs
```

---

## Conditional

This command's GitHub actions only work if GitHub PM was detected during `pongogo init`.

---

## Related

- Instruction: `instructions/_pongogo_core/issue_closure.instructions.md`
- Triggers: `/pongogo-retro` before closing (if preference set)
