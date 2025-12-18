---
title: "Git Safety Protocols"
description: "Comprehensive git safety protocols preventing destructive operations, mass content deletion, and data loss through systematic safeguards"
version: "1.0.0"
last_updated: "2025-12-18T17:52:00-05:00"
applies_to:
  - "**/*"
domains:
  - "safety_prevention"
  - "systematic_prevention"
priority: "P1"
patterns:
  - "safety_prevention"
  - "systematic_prevention"
  - "validation_first_execution"
routing:
  priority: 1
  triggers:
    keywords:
      - git safety
      - destructive git
      - git reset
      - force push
      - mass deletion
      - backup branch
      - git stash
      - protected branch
      - pre-commit hook
      - content deletion
    nlp: "Preventing destructive git operations, mass content deletion, force push protection, backup creation before risky operations"
---

# Git Safety Protocols

**Purpose**: Prevent destructive git operations, mass content deletion, and data loss through systematic safeguards and validation gates.

**Philosophy**: Data preservation over convenience - explicit confirmation required for any operation risking data loss.

---

## When to Apply

Apply these protocols when:

- Performing any git operation that modifies history (reset, rebase, amend)
- Committing substantial content deletions (>1000 lines or >50% file content)
- Working with protected infrastructure files (workflows, templates, configs)
- Force pushing to any branch
- Cleaning working directory or removing untracked files
- Modifying pre-commit hooks or bypassing validation

---

## Quick Reference

**Most Common Safe Patterns**:

**1. Safe Undo (Instead of Hard Reset)**:
```bash
# Dangerous: Loses uncommitted work
git reset --hard HEAD

# Safe: Stash changes for recovery
git stash push -m "backup before cleanup"
git checkout .
```

**2. Backup Before Destructive Operation**:
```bash
# Always create backup branch first
git branch backup-$(date +%Y%m%d-%H%M%S)
git rebase main
```

**3. Detect Large Deletions**:
```bash
# Check diff stats before committing
git diff --stat
# If >1000 lines deleted, verify intentional
```

**4. Protected File Check**:
```bash
# Verify no accidental changes to critical files
git diff --name-only | grep -E "\.github/|docs/|\.instructions\.md"
```

**5. Never Force Push to Main**:
```bash
# NEVER do this
git push --force origin main

# If really needed, use --force-with-lease
git push --force-with-lease origin feature-branch
```

---

## Core Principles

- **Explicit Confirmation**: Never execute destructive operations without user understanding of consequences
- **Backup First**: Create backup branches before major operations
- **Safer Alternatives**: Prefer `git stash`, `git checkout` over `git reset --hard`
- **Content Deletion Detection**: Flag commits removing >1000 lines or >50% of file content
- **Protected Files**: Extra validation for critical infrastructure

## Step-by-Step Guidance

### 1. **Assess Operation Risk Level**
   - Categorize as: Safe (checkout, status, log), Risky (reset, force push), Destructive (reset --hard, clean -f)
   - For Risky/Destructive: Require explicit user confirmation with explanation
   - For mass content deletion: Trigger content reduction assessment
   - Expected outcome: Operation risk level identified

### 2. **Content Reduction Assessment (Pre-Commit)**
   - Run `git diff --stat` before any commit
   - Flag commits removing >1000 lines
   - Flag commits reducing file content by >50%
   - Flag any critical file becoming empty
   - Expected outcome: Mass deletion detected before commit

### 3. **Protected Infrastructure Validation**
   - Never empty instruction files without explicit rationale
   - Never empty issue templates
   - Never empty workflow files
   - Never empty documentation without migration plan
   - Expected outcome: Critical infrastructure protected from accidental deletion

### 4. **Create Backup Before Destructive Operations**
   - Create backup branch: `git branch backup-$(date +%Y%m%d-%H%M%S)`
   - Verify backup exists before proceeding
   - Document backup branch in work log or issue comment
   - Expected outcome: Recovery path available if operation fails

### 5. **Execute with Validation**
   - Use `git show --stat HEAD~1..HEAD` to review changes after commit
   - Confirm empty files are intentionally empty
   - Document rationale for mass content removal in commit message
   - Run CI/CD validations before push
   - Expected outcome: Changes validated before becoming permanent

### 6. **Post-Operation Verification**
   - Verify expected files still exist: `ls -la key-directories/`
   - Check file sizes haven't dramatically changed: `du -sh target-files`
   - Run test suite to catch functional breakage
   - Review git log for unintended changes
   - Expected outcome: Operation completed successfully without data loss

## Examples

### Example 1: Safe Alternative to Destructive Reset

Scenario: Developer wants to discard uncommitted changes

```bash
# DANGEROUS: Destroys uncommitted work permanently
git reset --hard HEAD

# SAFE ALTERNATIVE 1: Preserve changes in stash
git stash push -m "backup before reset $(date +%Y%m%d-%H%M%S)"
# Later can recover: git stash pop

# SAFE ALTERNATIVE 2: Create backup branch
git branch backup-uncommitted-$(date +%Y%m%d-%H%M%S)
git add -A
git commit -m "Backup before reset"
git reset --hard HEAD~1

# SAFE ALTERNATIVE 3: Selective file revert
git checkout -- specific-file.ts
# Only reverts specific files, preserves others
```

**Context**: Stash or backup branch provides recovery path if reset was mistake
**Expected Result**: Changes preserved for potential recovery

### Example 2: Mass Content Deletion Detection

Scenario: Commit inadvertently empties instruction files

```bash
# Pre-commit validation script (should be in .git/hooks/pre-commit)
#!/bin/bash

# Get diff statistics
DIFF_STAT=$(git diff --cached --stat)

# Check for large deletions
DELETIONS=$(echo "$DIFF_STAT" | grep -oP '\d+(?= deletion)')
if [ ! -z "$DELETIONS" ] && [ "$DELETIONS" -gt 1000 ]; then
  echo "WARNING: This commit removes $DELETIONS lines"
  echo "Large content deletion detected - please review carefully"
  echo ""
  echo "Files affected:"
  git diff --cached --stat | grep "| .*-"
  echo ""
  read -p "Proceed with commit? (yes/no): " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "Commit aborted"
    exit 1
  fi
fi

exit 0
```

**Context**: Automated pre-commit hook prevents accidental mass deletion
**Expected Result**: User explicitly confirms large deletions, preventing mistakes

### Example 3: Protected Branch Operations

Scenario: Force pushing to main branch

```bash
# DANGEROUS: Force push without protection
git push --force origin main

# SAFE APPROACH: Protected branch workflow

# Step 1: Create backup branch first
git branch backup-main-$(date +%Y%m%d-%H%M%S)
git push origin backup-main-$(date +%Y%m%d-%H%M%S)

# Step 2: Use --force-with-lease (safer than --force)
git push --force-with-lease origin main
# Fails if remote changed since last fetch, preventing overwrites

# Step 3: Verify push success
git log origin/main --oneline -n 5

# If force push absolutely necessary:
# 1. Document reason in work log
# 2. Notify team in advance
# 3. Create backup branch
# 4. Use --force-with-lease
# 5. Verify result immediately
```

**Context**: Protected branches require extra validation and backup
**Trade-offs**: --force-with-lease safer than --force, but both should be rare and documented

## Validation Checklist

Before executing potentially destructive git operations:

### Risk Assessment
- [ ] Operation risk level identified (Safe/Risky/Destructive)
- [ ] User confirmation obtained for Risky/Destructive operations
- [ ] Consequences explained clearly to user
- [ ] Safer alternatives considered and rejected with rationale

### Content Protection
- [ ] `git diff --stat` reviewed for large deletions
- [ ] No critical files becoming empty unintentionally
- [ ] No templates or workflows being deleted accidentally
- [ ] Content reduction rationale documented in commit message

### Backup Creation
- [ ] Backup branch created: `backup-$(date +%Y%m%d-%H%M%S)`
- [ ] Backup branch pushed to remote (for critical operations)
- [ ] Backup documented in work log or issue comment
- [ ] Recovery procedure documented

### Post-Operation Validation
- [ ] Expected files still exist
- [ ] File sizes reasonable (not dramatically reduced)
- [ ] Test suite passes
- [ ] CI/CD validations pass
- [ ] Git log reviewed for unintended changes

## Common Pitfalls

### Pitfall 1: Using `git reset --hard` Without Backup

- **Problem**: Destroys uncommitted work permanently, no recovery path
- **Why it happens**: Quick fix for "undo everything" without thinking
- **Solution**: Use `git stash` or create backup branch first

### Pitfall 2: Force Pushing Without `--force-with-lease`

- **Problem**: `--force` overwrites remote changes made by others
- **Why it happens**: Unaware of safer alternative
- **Solution**: Always use `--force-with-lease` which fails if remote changed

### Pitfall 3: Bypassing Pre-Commit Hooks

- **Problem**: Using `--no-verify` to skip validation, committing problematic code
- **Why it happens**: Impatience or not understanding why hook failed
- **Solution**: Fix the actual issue causing hook failure

### Pitfall 4: Mass Content Deletion Without Review

- **Problem**: Committing large deletions without verifying intentionality
- **Why it happens**: Not reviewing `git diff` before committing
- **Solution**: Always run `git diff --stat` and review substantial deletions

## Edge Cases

### Edge Case 1: Emergency Rollback Required

**When**: Production issue requires immediate revert, normal process too slow
**Approach**:
- Create backup branch even in emergency
- Document emergency action in incident log
- Use `git revert` instead of `git reset` when possible (preserves history)
- Follow up with proper fix after incident resolved

### Edge Case 2: Pre-Commit Hook False Positive

**When**: Legitimate change flagged as problematic by pre-commit hook
**Approach**:
- Investigate why hook flagged the change
- Verify change is actually safe
- Document rationale for override
- Use `--no-verify` only if absolutely necessary
- Report false positive to improve hook logic

### Edge Case 3: Corrupted Repository State

**When**: Repository in inconsistent state, normal git operations failing
**Approach**:
- Backup entire repository directory: `cp -r .git .git.backup`
- Try `git fsck` to identify corruption
- Attempt recovery with `git reflog`
- If unfixable, clone fresh and copy working directory changes

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Lost uncommitted work after reset | `git reset --hard` without backup | Check `git reflog`, may be recoverable |
| Force push rejected | Remote changed since last fetch | Use `git pull --rebase` then `--force-with-lease` |
| Pre-commit hook failing | Code doesn't meet quality standards | Fix the actual issue |
| Large deletion committed accidentally | No pre-commit validation | Revert commit: `git revert HEAD` |
| Cannot push to protected branch | Branch protection rules active | Use PR workflow |

---

**Success Criteria**: Zero unintended data loss through git operations, all destructive operations require explicit confirmation with backup creation, mass content deletions detected and validated before commit.
