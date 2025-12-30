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

### Zero-Config Install (Recommended)

The fastest way to get started:

```bash
curl -sSL https://get.pongogo.com | bash
```

The installer will:
1. Detect if Docker is available
2. If Docker present: Pull the Docker image and configure Claude Code
3. If no Docker: Offer interactive menu (install Docker or use pip)

### Docker Installation

Docker is the recommended method for security and consistency:

```bash
# Pull the image
docker pull ghcr.io/pongogo/pongogo-server:latest

# Configure Claude Code
pongogo setup-mcp
```

### pip Installation

For developers who prefer local Python:

```bash
pip install pongogo
pongogo setup-mcp
```

### Requirements

- **Docker** (recommended) OR Python 3.10+
- Claude Code installed

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

## Portability

The `.pongogo/` directory is designed to be **lean and portable**:

- **Commit to version control**: The entire `.pongogo/` directory should be committed
- **Multi-machine workflow**: Coworkers can `git pull` and immediately have working Pongogo
- **No local state**: No machine-specific paths, credentials, or large files
- **Independent init**: Each team member can run `pongogo init` on a fresh clone

### What Gets Stored

| Location | Contents | Portable? |
|----------|----------|-----------|
| `.pongogo/config.yaml` | Category toggles, placeholders | Yes |
| `.pongogo/instructions/` | Seeded instruction files | Yes |
| `.pongogo/instructions/manifest.yaml` | Version tracking | Yes |

### What Stays Local

These are NOT stored in `.pongogo/`:
- MCP server logs (stored in system logs)
- Cache files (regenerated on demand)
- User credentials (use environment variables)

---

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

Pongogo includes an MCP (Model Context Protocol) server that routes instructions to AI coding assistants.

### Configure Claude Code

```bash
# Auto-detect Docker/pip and configure Claude Code
pongogo setup-mcp

# Preview configuration without changes
pongogo setup-mcp --dry-run

# Force overwrite existing configuration
pongogo setup-mcp --force
```

This adds the Pongogo MCP server to your `~/.claude.json` configuration.

### Upgrade Pongogo

Use the `/pongogo-upgrade` slash command in Claude Code to upgrade to the latest version.

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
- ✅ MCP server with Docker/pip distribution
- ✅ `pongogo setup-mcp` Claude Code integration
- ✅ Upgrade mechanism via MCP tool
- 📋 CI/CD for Docker image publishing (planned)

See [pongogo/pongogo](https://github.com/pongogo/pongogo) for development progress.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/pongogo/pongogo-to-go.git
cd pongogo-to-go

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify setup
pre-commit run --all-files
```

### Development Commands

```bash
# Run all pre-commit hooks
make pre-commit

# Linting only
make lint

# Formatting only
make format

# Type checking only
make typecheck

# Run tests
make test
```

### Daily Workflow

Pre-commit hooks run automatically on `git commit`. To run manually:

```bash
# Check all files
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "Emergency fix"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hook fails on first run | Run `pre-commit run --all-files` to fix formatting |
| Mypy import errors | Add type stubs to `additional_dependencies` in `.pre-commit-config.yaml` |
| Slow mypy execution | Mypy caches results; subsequent runs are faster |
| ruff conflict with editor | Configure editor to use project ruff settings |

## License

MIT License - see [LICENSE](LICENSE)
