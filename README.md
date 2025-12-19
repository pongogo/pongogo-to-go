# Pongogo

Portable AI agent knowledge routing system. Install Pongogo on any repository to get intelligent instruction routing for AI coding assistants.

## Quick Start

```bash
# Install Pongogo
pip install pongogo

# Initialize in your repository
cd your-project
pongogo init
```

This creates a `.pongogo/` directory with configuration and seeded instruction files that help AI assistants understand your project's patterns and practices.

## Installation

### Requirements

- Python 3.10 or higher
- pip

### Install from PyPI

```bash
pip install pongogo
```

### Install from source

```bash
git clone https://github.com/pongogo/pongogo-to-go.git
cd pongogo-to-go
pip install -e .
```

## Usage

### Initialize Pongogo

```bash
pongogo init
```

Creates a `.pongogo/` directory in your current working directory with:

- `config.yaml` - Configuration for enabling/disabling instruction categories
- `instructions/` - Seeded instruction files (31 files across 12 categories)

### Command Options

| Flag | Short | Description |
|------|-------|-------------|
| `--minimal` | `-m` | Install only core instruction categories (software_engineering, safety_prevention) |
| `--force` | `-f` | Overwrite existing `.pongogo/` directory |
| `--no-interactive` | `-y` | Accept all defaults without prompting |
| `--help` | | Show help message |

### Examples

```bash
# Interactive setup (prompts for options)
pongogo init

# Non-interactive with all defaults
pongogo init --no-interactive

# Minimal installation (6 core files only)
pongogo init --minimal

# Overwrite existing installation
pongogo init --force

# CI/CD usage
pongogo init --no-interactive --minimal
```

## What Gets Created

```
your-project/
└── .pongogo/
    ├── config.yaml              # Enable/disable instruction categories
    └── instructions/
        ├── manifest.yaml        # Instruction file metadata
        ├── software_engineering/
        │   ├── python_script_development.instructions.md
        │   ├── commit_message_format.instructions.md
        │   └── git_safety.instructions.md
        ├── project_management/
        │   └── ... (6 files)
        ├── agentic_workflows/
        │   └── ... (4 files)
        └── ... (9 more categories)
```

## Configuration

After initialization, customize `.pongogo/config.yaml`:

```yaml
# Enable/disable instruction categories
categories:
  software_engineering: true
  project_management: true
  agentic_workflows: true
  # ... set to false to disable

# Customize placeholders for your project
placeholders:
  wiki_path: wiki/
  docs_path: docs/
  owner_repo: your-org/your-repo
  instructions_path: .pongogo/instructions/
```

## Instruction Categories

| Category | Files | Description |
|----------|-------|-------------|
| software_engineering | 3 | Git safety, commit formats, Python standards |
| project_management | 6 | Work logging, scope prevention, glossary |
| agentic_workflows | 4 | Agent decision making, compliance, multi-pass analysis |
| architecture | 1 | Repository organization |
| quality | 2 | PR workflows, environment configuration |
| safety_prevention | 3 | Validation-first execution, systematic prevention |
| testing | 1 | Observability testing patterns |
| validation | 3 | Verification efficiency, deterministic validation |
| devops | 2 | Audit logging, observability patterns |
| development | 1 | Token usage and context management |
| github_integration | 2 | GitHub essentials, sub-issues |
| trust_execution | 3 | Trust-based execution, feature development |

## MCP Server Integration

Pongogo includes an MCP (Model Context Protocol) server that routes instructions to AI coding assistants. Configuration instructions coming soon.

## Architecture

Pongogo uses a two-layer architecture:

| Layer | Repository | Purpose |
|-------|------------|---------|
| **Pongogo** | This repo (`pongogo-to-go`) | The product - what you install |
| **Super Pongogo** | `pongogo/pongogo` | Internal development tooling |

This separation ensures external users get a clean, focused product while internal development infrastructure remains separate.

## Status

🚧 **Under Development** - P05 "Pongogo to Go" milestone

Current capabilities:
- ✅ `pongogo init` CLI
- ✅ Seeded instruction files (31 files, 12 categories)
- 🔄 MCP server integration (in progress)
- 📋 Remote updates (planned)

See [pongogo/pongogo](https://github.com/pongogo/pongogo) for development progress.

## License

MIT License - see [LICENSE](LICENSE)
