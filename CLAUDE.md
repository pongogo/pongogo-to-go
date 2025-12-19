# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project Home**: [pongogo.com](https://pongogo.com)

Pongogo is a portable AI agent knowledge routing system. This repository contains the product that external users install on their repositories.

## Status

🚧 **Under Development** - Repository structure being established.

## Architecture

This is the **product repository** in Pongogo's two-layer architecture:

- **This repo** (`pongogo-to-go`): The installable product
- **Super Pongogo** (`pongogo/pongogo`): Internal development tooling

## Directory Structure

```
src/                    # Source code
  mcp-server/           # MCP knowledge routing server
  cli/                  # pongogo init CLI

instructions/           # Seeded instruction sets
  _pongogo_core/        # Core routing instructions (always on)
  software_engineering/ # Optional SE best practices
  project_management/   # Optional PM methodology

docs/                   # Documentation
```

## Development

For development work on Pongogo itself, see [pongogo/pongogo](https://github.com/pongogo/pongogo).
