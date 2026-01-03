---
description: Upgrade Pongogo to latest version
---

# Pongogo Upgrade

Upgrade Pongogo to the latest version.

## Usage

```
/pongogo-upgrade
```

## Execution

**Execute silently and display only the formatted output.**

## User Experience

The user sees ONLY the result - never the technical operations.

**What the user sees**:
- Version comparison
- Brief "Upgrading..." indicator
- Changelog / what's new
- "Please exit and re-enter Claude Code"

**What the user does NOT see**:
- Docker commands
- pip commands
- Container restarts
- Download progress
- Any technical output

## Execution (Invisible to User)

1. Check current vs latest version (silent)
2. Download artifacts (silent)
3. Restart MCP server (silent)
4. Refresh instructions if needed (silent)
5. Display result to user

## Output

### Update Available

```
## Pongogo Upgrade

Upgrading v1.2.3 → v1.3.0...

Done.

### What's New
- [Feature 1]
- [Feature 2]

Please exit and re-enter Claude Code.
```

### Already Current

```
You're on the latest version (v1.2.3).
```

### Error

```
Upgrade failed: [brief reason]

Run `/pongogo-status` for diagnostics.
```
