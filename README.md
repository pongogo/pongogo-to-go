# Pongogo

Portable AI agent knowledge routing system. Install Pongogo on any repository to get intelligent instruction routing for AI coding assistants.

## Vision

Pongogo provides a knowledge routing MCP server that surfaces the right instructions at the right time for AI coding assistants like Claude Code, GitHub Copilot, and others.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Your Repository                              │
├─────────────────────────────────────────────────────────────────┤
│  .pongogo/                    # Created by `pongogo init`        │
│  ├── config.yaml              # instruction_sets toggles         │
│  ├── instructions/            # Seeded best practices            │
│  │   ├── _pongogo_core/       # Always on (routing, PI lifecycle)│
│  │   ├── software_engineering/# Optional (commit, PR, etc.)      │
│  │   └── project_management/  # Optional (task scoping, retros)  │
│  └── potential_improvements.db│ Track improvement candidates     │
│                                                                  │
│  knowledge/instructions/      # Your custom instruction files    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Coming soon
pongogo init
```

## Features

- **Intelligent Routing**: Surfaces relevant instructions based on your current task
- **Seeded Instructions**: Best practice instruction sets you can toggle on/off
- **Custom Instructions**: Add your own project-specific instructions
- **Potential Improvements**: Track patterns that could become instructions
- **MCP Integration**: Works with Claude Code and other MCP-compatible tools

## Architecture

Pongogo uses a two-layer architecture:

| Layer | Repository | Purpose |
|-------|------------|---------|
| **Pongogo** | This repo (`pongogo-to-go`) | The product - what you install |
| **Super Pongogo** | `pongogo/pongogo` | Internal dev tooling |

This separation ensures external users get a clean, focused product while we maintain internal development infrastructure separately.

## Status

🚧 **Under Development** - P05 "Pongogo to Go" milestone

See [pongogo/pongogo](https://github.com/pongogo/pongogo) for development progress.

## License

MIT License - see [LICENSE](LICENSE)
