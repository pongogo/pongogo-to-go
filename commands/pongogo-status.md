# MCP Server Status

Check the status of the Pongogo MCP server.

---

## What This Does

1. Shows current server state:
   - Enabled / Disabled / Simulate
   - Routing engine version
   - Loaded instruction count

2. Allows mode changes

---

## Usage

```
/pongogo-status
```

---

## Status Output

```
Pongogo MCP Server Status
-------------------------
State: Enabled
Engine: durian-0.6
Instructions: 47 loaded
Preferences: 5 learned
```

---

## Mode Commands

| Command | Action |
|---------|--------|
| `/pongogo-status` | Show current status |
| `/pongogo-status enable` | Enable routing |
| `/pongogo-status disable` | Disable routing |
| `/pongogo-status simulate` | Enable simulate mode (logs but doesn't execute) |

---

## Modes

### Enabled (Default)
- Full routing active
- Instructions route and execute
- Preferences apply

### Disabled
- No routing occurs
- Pongogo is silent
- Manual commands still work

### Simulate
- Routing occurs and logs
- Shows what would happen
- Doesn't execute actions
- Useful for testing/debugging

---

## Related

- Config: `.pongogo/config.yaml`
- Preferences: `.pongogo/preferences.yaml`
