---
description: Run comprehensive diagnostics for troubleshooting
---

# Pongogo Diagnose

Run comprehensive diagnostics to verify Pongogo installation and generate a support bundle.

## Usage

```
/pongogo-diagnose           # Full diagnostics
/pongogo-diagnose --brief   # Quick check only
```

## Execution

**IMPORTANT: Run all diagnostic checks QUIETLY and display ONLY the final formatted diagnostic report.**

- Do NOT show intermediate output, progress messages, or thinking aloud
- Do NOT display individual tool call results to the user
- Suppress all user-facing messaging during data gathering
- Execute each check silently, then aggregate results into the final report
- The user should see ONLY the formatted "## Pongogo Diagnostic Report" output below

Run all diagnostic checks and generate a formatted report. This report can be shared with support.

### Diagnostic Checks

#### 1. Environment Info
Gather system context (safe to share, no secrets):

```bash
# OS and architecture
uname -s -m

# Docker version
docker --version 2>/dev/null || echo "Docker not found"
```

#### 2. Configuration Validation

Check `.pongogo/` directory:
- [ ] `.pongogo/config.yaml` exists and is valid YAML
- [ ] `.pongogo/instructions/` directory exists
- [ ] Count instruction files: `find .pongogo/instructions -name "*.md" | wc -l`
- [ ] Count categories: `ls -d .pongogo/instructions/*/ | wc -l`

Check `.mcp.json`:
- [ ] File exists at project root
- [ ] Contains `pongogo-knowledge` server entry
- [ ] Docker command path is valid

#### 3. MCP Server Connection

Use MCP tools to verify connection and get version info:

**Get routing engine version**:
- Call `get_routing_info()` via MCP
- Extract `engine` from response (e.g., "durian-0.6.1")

**Get pongogo package version**:
- Call `upgrade_pongogo()` via MCP
- Extract `current_version` from response

**Test routing**:
- [ ] Call `route_instructions` with test query "how do I commit code?"
- [ ] Verify returns > 0 results
- [ ] Record response time

#### 4. Event History

Check routing event capture health using `get_routing_event_stats()` MCP tool:

- [ ] Call `get_routing_event_stats()` via MCP
- [ ] Check `status` field: "active", "empty", or "missing"
- [ ] Note `total_count` for total events captured
- [ ] Note `last_event` timestamp and calculate relative time
- [ ] Note `last_24h_count` for recent activity

**Status Interpretation**:
- **active**: Database exists with events - healthy state
- **empty**: Database exists but no events yet - recently initialized
- **missing**: No database file - `pongogo init` may not have been run

#### 5. Routing Validation

Test routing with known queries that should return results:

| Test Query | Expected Category | Pass/Fail |
|------------|-------------------|-----------|
| "how do I commit code?" | software_engineering | |
| "git safety" | safety_prevention | |
| "work log entry" | project_management | |

#### 6. Network Connectivity (if MCP connection fails)

```bash
# Can reach container registry (run on HOST via Bash tool)
curl -s -o /dev/null -w "%{http_code}" https://pongogo.azurecr.io/v2/ 2>/dev/null
```

### Output Format

Generate a copyable diagnostic report:

```markdown
## Pongogo Diagnostic Report

**Generated**: [timestamp]
**Pongogo Version**: [from upgrade_pongogo MCP tool]
**Routing Engine**: [from get_routing_info MCP tool, e.g., durian-0.6.1]

### Environment
- **OS**: [uname output]
- **Docker**: [version or "not found"]
- **Architecture**: [arm64/amd64]

### Configuration
- **Config file**: ✅ Valid / ❌ Missing / ⚠️ Invalid
- **Instructions**: [count] files in [count] categories
- **MCP config**: ✅ Valid / ❌ Missing / ⚠️ Invalid

### MCP Server
- **Status**: ✅ Connected / ❌ Not connected
- **Version**: [from upgrade_pongogo response]

### Event History
- **Status**: ✅ Active / ⚠️ Empty / ❌ Missing
- **Total Events**: [count]
- **Last Event**: [timestamp] ([relative time, e.g., "2 hours ago"])
- **24h Activity**: [count] events

### Routing Tests
| Query | Result | Time |
|-------|--------|------|
| commit code | ✅ 3 matches | 45ms |
| git safety | ✅ 2 matches | 38ms |
| work log | ✅ 1 match | 42ms |

### Overall Status
[✅ All systems operational / ⚠️ Issues detected / ❌ Critical failure]

### Issues Found
[List any problems detected]

### Recommended Actions
[Specific fix commands if issues found]
```

### Support Integration

If issues are found, offer to generate support request:

```
Issues detected. To get help:

1. Copy the diagnostic report above
2. Open: https://github.com/pongogo/pongogo-to-go/issues/new
3. Paste the report and describe your issue

Or run `/pongogo-support` to open an issue directly.
```

### Quick Fixes Reference

| Issue | Fix |
|-------|-----|
| MCP not connected | Restart Claude Code, allow MCP server when prompted |
| Image not found | `pongogo upgrade` or `docker pull pongogo.azurecr.io/pongogo:stable` |
| Config invalid | `pongogo init --force` |
| No instructions | `pongogo init` |
| Routing returns 0 | Check `.pongogo/instructions/` exists and has `.md` files |
| Event history missing | `pongogo init` to create `.pongogo/sync/` directory |
| Event history empty | Normal for new installs; events captured on first route call |

**NOTE**: Pongogo-to-Go runs via Claude Code's MCP infrastructure. Do NOT suggest `docker-compose` commands - they don't apply here.

### Privacy Note

The diagnostic report contains:
- ✅ System info (OS, Docker version)
- ✅ File counts and paths
- ✅ Routing test results
- ❌ NO file contents
- ❌ NO personal data
- ❌ NO API keys or secrets
