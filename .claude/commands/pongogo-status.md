---
description: MCP server status (enabled/disabled/simulate)
---

# Pongogo Status

Quick health check for Pongogo knowledge routing.

## Usage

```
/pongogo-status
```

## Execution

Execute silently and display only the formatted output.

### Checks Performed

1. Read `.pongogo-mcp-state.json` for mode
2. Check container status
3. Test routing with sample query

## Output

```
## Pongogo Status

**Mode**: [ENABLED | DISABLED | SIMULATE]
**Container**: [Up | Down]
**Routing**: [Working | Failed]
```

If all pass:
```
All systems operational.
```

If any fail, show the relevant fix:

- Container down: `docker-compose up -d pongogo`
- Routing failed: `docker-compose build pongogo && docker-compose up -d pongogo`
- MCP unavailable: Check `~/.claude/mcp_settings.json`

### Related Commands

- `/pongogo-enable` `/pongogo-disable` - Toggle routing
- `/pongogo-simulate-enable` `/pongogo-simulate-disable` - Test mode
- `/pongogo-dry-run` - One-off routing test
- `/pongogo-config` - Edit preferences
