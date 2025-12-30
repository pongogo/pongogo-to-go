# Pre-commit Configuration Specification

**Issue**: [#371](https://github.com/pongogo/pongogo/issues/371) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document specifies the pre-commit hook configuration for pongogo-to-go, providing fast local feedback on code quality before commits.

**Core Purpose**: Catch code quality issues before they reach CI, enabling fast developer feedback.

**Position in Test Pyramid**: Layer 1 (Pre-commit Hooks) - runs locally, instant feedback.

---

## Tool Selection

### Selected Tools

| Tool | Purpose | Why Selected |
|------|---------|--------------|
| `ruff` | Linting + formatting | Fast (Rust-based), replaces black/isort/flake8 |
| `ruff-format` | Code formatting | Consistent style, integrated with ruff |
| `mypy` | Type checking | Catch type errors before runtime |

### Rejected Alternatives

| Tool | Reason Not Selected |
|------|---------------------|
| `black` | Replaced by `ruff-format` (faster, same output) |
| `isort` | Replaced by `ruff` import sorting |
| `flake8` | Replaced by `ruff` linting |
| `pylint` | Slower, `ruff` covers most rules |

---

## Pre-commit Configuration

### .pre-commit-config.yaml

```yaml
# .pre-commit-config.yaml
# Pre-commit hooks for pongogo-to-go
# Run: pre-commit run --all-files

# Minimum pre-commit version required
minimum_pre_commit_version: "3.0.0"

# Default stages (can be overridden per hook)
default_stages: [pre-commit]

# Fail fast - stop on first failure
fail_fast: false

repos:
  # =========================================================================
  # Ruff - Fast Python linting and formatting
  # =========================================================================
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4  # Use latest stable version
    hooks:
      # Linting with auto-fix
      - id: ruff
        name: ruff (lint)
        args: [--fix, --exit-non-zero-on-fix]
        types_or: [python, pyi]

      # Formatting (replaces black)
      - id: ruff-format
        name: ruff (format)
        types_or: [python, pyi]

  # =========================================================================
  # Mypy - Static type checking
  # =========================================================================
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1  # Use latest stable version
    hooks:
      - id: mypy
        name: mypy (type check)
        # Only check src/ and tests/ directories
        files: ^(src|tests)/
        # Additional type stubs
        additional_dependencies:
          - types-PyYAML>=6.0.0
          - types-requests>=2.31.0
          - pydantic>=2.0.0
        args:
          - --config-file=pyproject.toml

  # =========================================================================
  # Standard pre-commit hooks
  # =========================================================================
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      # Prevent large files from being committed
      - id: check-added-large-files
        args: [--maxkb=500]

      # Check for files that would conflict on case-insensitive filesystems
      - id: check-case-conflict

      # Check for merge conflict markers
      - id: check-merge-conflict

      # Ensure files end with newline
      - id: end-of-file-fixer

      # Remove trailing whitespace
      - id: trailing-whitespace
        args: [--markdown-linebreak-ext=md]

      # Check YAML syntax
      - id: check-yaml
        args: [--unsafe]  # Allow custom tags

      # Check TOML syntax
      - id: check-toml

      # Validate Python AST
      - id: check-ast
```

### Version Pinning Strategy

| Approach | Description |
|----------|-------------|
| **Exact major.minor** | Pin to `vX.Y.Z` for reproducibility |
| **Update frequency** | Monthly via Dependabot or manual |
| **Breaking changes** | Test locally before updating |

**Current Versions** (as of 2025-12-30):
- ruff-pre-commit: v0.8.4
- mirrors-mypy: v1.14.1
- pre-commit-hooks: v5.0.0

---

## pyproject.toml Configuration

### Ruff Configuration

```toml
# =============================================================================
# Ruff - Linting and Formatting
# =============================================================================
[tool.ruff]
# Target Python version
target-version = "py310"

# Line length (same as ruff-format default)
line-length = 88

# Source directories
src = ["src", "tests"]

# Exclude directories
exclude = [
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
]

[tool.ruff.lint]
# Enable rule sets
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]

# Ignore specific rules
ignore = [
    "E501",   # Line too long (handled by formatter)
    "B008",   # Do not perform function calls in argument defaults (Typer pattern)
    "B904",   # Within except clause, raise with `from` (too strict)
]

# Allow autofix for all enabled rules
fixable = ["ALL"]
unfixable = []

[tool.ruff.lint.isort]
# Known first-party imports
known-first-party = ["cli", "mcp_server"]

[tool.ruff.format]
# Use double quotes (consistent with black)
quote-style = "double"

# Indent with spaces
indent-style = "space"

# Respect magic trailing commas
skip-magic-trailing-comma = false

# Format docstrings
docstring-code-format = true
```

### Mypy Configuration

```toml
# =============================================================================
# Mypy - Type Checking
# =============================================================================
[tool.mypy]
# Python version
python_version = "3.10"

# Source paths
files = ["src", "tests"]

# Strict mode subset (gradually increase)
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start permissive, tighten later
check_untyped_defs = true

# Import handling
ignore_missing_imports = true  # Third-party stubs not always available

# Error output
show_error_codes = true
show_column_numbers = true
pretty = true

# Per-module overrides
[[tool.mypy.overrides]]
module = "tests.*"
# Allow untyped defs in tests (more pragmatic)
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = [
    "fastmcp.*",
    "watchdog.*",
]
# External packages without stubs
ignore_missing_imports = true
```

---

## Dev Dependencies Update

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-docker>=2.0.0",

    # Linting and formatting
    "ruff>=0.8.0",

    # Type checking
    "mypy>=1.14.0",
    "types-PyYAML>=6.0.0",
    "types-requests>=2.31.0",

    # Pre-commit
    "pre-commit>=3.0.0",
]
```

---

## Developer Setup Instructions

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/pongogo/pongogo-to-go.git
cd pongogo-to-go

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# 3. Install with dev dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify setup
pre-commit run --all-files
```

### Daily Usage

```bash
# Hooks run automatically on git commit
git add .
git commit -m "Your message"
# → Hooks run automatically

# Manual full check
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate

# Skip hooks (emergency only)
git commit --no-verify -m "Emergency fix"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hook fails on first run | Run `pre-commit run --all-files` to fix formatting |
| Mypy import errors | Add type stubs to `additional_dependencies` |
| Slow mypy execution | Use `--fast` flag or limit files |
| ruff conflict with editor | Configure editor to use project ruff settings |

---

## CI Integration

### Same Checks in CI

```yaml
# .github/workflows/ci.yml (excerpt)
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run pre-commit
        uses: pre-commit/action@v3.0.1
        with:
          extra_args: --all-files --show-diff-on-failure
```

### Makefile Targets

```makefile
# Makefile
.PHONY: lint format typecheck

# Run all linting
lint:
	ruff check src/ tests/

# Run formatter
format:
	ruff format src/ tests/

# Run type checker
typecheck:
	mypy src/ tests/

# Run all pre-commit hooks
pre-commit:
	pre-commit run --all-files
```

---

## Performance Targets

| Metric | Target | Enforcement |
|--------|--------|-------------|
| Total execution | < 30 seconds | Typical full run |
| ruff (lint + format) | < 5 seconds | Very fast (Rust) |
| mypy | < 25 seconds | Slower, caches results |
| Standard hooks | < 2 seconds | Minimal overhead |

### Performance Tips

1. **Incremental runs**: Pre-commit only checks changed files
2. **Mypy daemon**: Use `dmypy` for faster repeated runs
3. **Skip slow hooks**: `SKIP=mypy git commit -m "Quick fix"` (use sparingly)
4. **Cache warmup**: First run is slower, subsequent runs use cache

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `.pre-commit-config.yaml` with all hooks
- [ ] Add ruff configuration to `pyproject.toml`
- [ ] Add mypy configuration to `pyproject.toml`
- [ ] Update dev dependencies in `pyproject.toml`
- [ ] Create Makefile with lint/format/typecheck targets
- [ ] Test hooks run successfully on entire codebase
- [ ] Add developer setup instructions to README
- [ ] Verify CI runs same checks

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Test Pyramid: `docs/design/test_pyramid_layers.md`
- Ruff Documentation: https://docs.astral.sh/ruff/
- Mypy Documentation: https://mypy.readthedocs.io/
- Pre-commit Documentation: https://pre-commit.com/
