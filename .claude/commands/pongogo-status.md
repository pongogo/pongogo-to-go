---
description: Check Pongogo MCP server health
---

# Pongogo Status

Quick health check for Pongogo knowledge routing.

## Usage

```
/pongogo-status
```

## Execution

**IMPORTANT**: Do NOT check for state files, docker containers, or docker-compose. Pongogo-to-Go runs via Claude Code's MCP infrastructure, not as a standalone container.

**Step 1**: Call the `get_routing_info()` MCP tool (from pongogo-knowledge server).

**Step 2**: Display the result.

If the MCP tool call succeeds, output EXACTLY:

```
## Pongogo Status ✅

**Routing Engine**: [engine value from response]
**Instructions Loaded**: [instruction_count value from response] (includes core + seeded)

All systems operational.
```

If the MCP tool call fails or is not available, output EXACTLY:

```
## Pongogo Status ❌

MCP server not connected.

**Fix**:
1. Restart Claude Code
2. When prompted, allow the pongogo-knowledge MCP server
3. Run `/mcp` to verify connection
```

**DO NOT**:
- Check for `.pongogo-mcp-state.json` (doesn't exist in pongogo-to-go)
- Check for running Docker containers (MCP manages this)
- Suggest `docker-compose` commands (not used in pongogo-to-go)
- Show "Mode" (pongogo-to-go is always enabled when connected)
