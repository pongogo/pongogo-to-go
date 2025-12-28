# Pongogo Roadmap

Public roadmap for Pongogo - the portable AI agent knowledge routing system.

**Last Updated**: 2025-12-23

---

## Current Release

### v0.1.0 (In Development)

The initial release focuses on the core `pongogo init` experience:

- **CLI Installation**: `pip install pongogo`
- **Repository Initialization**: `pongogo init` creates `.pongogo/` directory
- **Seeded Instructions**: 31 instruction files across 12 categories
- **Category Toggles**: Enable/disable instruction categories via `config.yaml`
- **Wiki/Docs Detection**: Detects existing knowledge folders during init

---

## Upcoming Features

### Orchestrator (Planned)

Automatic compliance enforcement for procedural instructions.

**What it does**:
- Monitors agent execution for procedural compliance
- Automatically corrects non-compliant behavior
- Preserves "vibe coding" experience - enforcement is transparent

**Use case**: When you say "close the issue", Pongogo ensures the full closure checklist runs, not just the API call.

---

### Auto-Compact Preparation (Planned)

Preserve work state across context compaction boundaries.

**What it does**:
- Detects when context window is running low
- Automatically saves current work state
- Restores state after compaction

**Use case**: Long coding sessions survive context limits without losing track of what you were doing.

---

### IDE Integrations (Planned)

Native support for popular development environments.

| IDE | Status |
|-----|--------|
| Claude Code (CLI) | Supported |
| VS Code | Planned |
| JetBrains IDEs | Planned |
| Cursor | Planned |
| Windsurf | Under consideration |

---

### MCP Server Distribution (Planned)

Standalone MCP server for advanced routing capabilities.

**What it does**:
- Semantic instruction routing based on context
- Real-time instruction discovery
- Routing analytics and observability

---

### Remote Updates (Future)

Keep seeded instructions up-to-date automatically.

**What it does**:
- Check for instruction updates from Pongogo registry
- Opt-in update mechanism
- Version pinning for stability

---

## Feature Requests

Have a feature request? Open an issue at [pongogo/pongogo-to-go](https://github.com/pongogo/pongogo-to-go/issues).

---

## Development Status

Pongogo is under active development. See [pongogo/pongogo](https://github.com/pongogo/pongogo) for development progress and milestone tracking.

| Milestone | Status | Description |
|-----------|--------|-------------|
| P05 | In Progress | Pongogo to Go extraction |
| P04 | Planned | Core refinement (Orchestrator) |
| P03 | Planned | Agent-first architecture |

---

## Versioning

Pongogo follows [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes to CLI or instruction format
- **Minor**: New features, new instruction categories
- **Patch**: Bug fixes, instruction content updates
