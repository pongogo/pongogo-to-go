---
description: Upgrade Pongogo to latest version
---

# Pongogo Upgrade

Upgrade Pongogo to the latest version with zero manual steps.

## Usage

```
/pongogo-upgrade
```

## What Happens

All operations execute automatically and transparently:

1. **Version Check** - Compare current vs latest available
2. **Download** - Pull new artifacts (Docker/pip as appropriate)
3. **Restart** - Restart MCP server container
4. **Refresh** - Update seeded instructions if schema changed
5. **Report** - Display changelog and completion status

## Output

### If Update Available

```
## Pongogo Upgrade

**Current**: v1.2.3
**Latest**: v1.3.0

Upgrading...
- Downloading new version
- Restarting MCP server
- Refreshing instructions

### What's New in v1.3.0
- [Feature 1]
- [Feature 2]
- [Bug fix 1]

Upgrade complete. Please exit and re-enter Claude Code to use the new version.
```

### If Already Current

```
## Pongogo Upgrade

You're running the latest version (v1.2.3).
```

### If Error

```
## Pongogo Upgrade

Upgrade failed: [error message]

**Manual recovery**:
[Specific steps if needed]
```

---

**Design Principle**: User should NOT need to run Docker commands, pip commands, or understand installation method. Everything happens automatically.
