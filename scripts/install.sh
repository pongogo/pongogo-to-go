#!/bin/bash
#
# Pongogo Installation Script
# https://get.pongogo.com
#
# Usage: curl -sSL https://get.pongogo.com | bash
#

set -e

# Colors for output (only if terminal supports it)
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m' # No Color
else
    GREEN=''
    YELLOW=''
    RED=''
    NC=''
fi

# Minimal output helper
info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin)
            PLATFORM="macos"
            ;;
        Linux)
            if grep -q Microsoft /proc/version 2>/dev/null; then
                PLATFORM="wsl"
            else
                PLATFORM="linux"
            fi
            ;;
        *)
            error "Unsupported platform: $(uname -s)"
            ;;
    esac
}

# Check if Docker is available and running
has_docker() {
    if command -v docker &> /dev/null; then
        docker info &> /dev/null 2>&1
        return $?
    fi
    return 1
}

# Install Docker based on platform
install_docker() {
    case "$PLATFORM" in
        macos)
            if command -v brew &> /dev/null; then
                info "Installing Docker Desktop via Homebrew..."
                brew install --cask docker
                echo ""
                warn "Docker Desktop installed. Please:"
                echo "  1. Open Docker Desktop from Applications"
                echo "  2. Complete the setup wizard"
                echo "  3. Run this script again"
                exit 0
            else
                error "Homebrew not found. Install from https://brew.sh first, or install Docker Desktop from https://docker.com"
            fi
            ;;
        linux)
            info "Installing Docker via get.docker.com..."
            curl -fsSL https://get.docker.com | sh
            sudo usermod -aG docker "$USER"
            warn "Docker installed. Log out and back in for group changes, then run this script again."
            exit 0
            ;;
        wsl)
            echo ""
            warn "For WSL, Docker Desktop for Windows is recommended:"
            echo "  1. Install Docker Desktop for Windows"
            echo "  2. Enable WSL 2 backend in Settings"
            echo "  3. Run this script again"
            exit 0
            ;;
    esac
}

# Install via pip
install_pip() {
    if command -v pip3 &> /dev/null; then
        info "Installing Pongogo via pip..."
        pip3 install --user pongogo
        info "Configuring Claude Code..."
        # Run setup-mcp if available
        if command -v pongogo &> /dev/null; then
            pongogo setup-mcp --force
        else
            warn "Run 'pongogo setup-mcp' to configure Claude Code"
        fi
    elif command -v pip &> /dev/null; then
        info "Installing Pongogo via pip..."
        pip install --user pongogo
        info "Configuring Claude Code..."
        pongogo setup-mcp --force 2>/dev/null || warn "Run 'pongogo setup-mcp' to configure Claude Code"
    else
        error "pip not found. Please install Python 3.10+ first."
    fi
}

# Docker-based installation
install_docker_based() {
    info "Pulling Pongogo Docker image..."
    docker pull ghcr.io/pongogo/pongogo-server:latest

    info "Configuring Claude Code..."

    # Configure Claude Code directly
    CLAUDE_CONFIG="$HOME/.claude.json"

    if [ -f "$CLAUDE_CONFIG" ]; then
        # Backup existing config
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup_$(date +%Y%m%d_%H%M%S)"
    fi

    # Create or update config
    if [ -f "$CLAUDE_CONFIG" ]; then
        # Use Python to merge config (handles JSON properly)
        python3 - "$CLAUDE_CONFIG" <<'PYTHON'
import json
import sys

config_path = sys.argv[1]
with open(config_path) as f:
    config = json.load(f)

if "mcpServers" not in config:
    config["mcpServers"] = {}

config["mcpServers"]["pongogo-knowledge"] = {
    "command": "docker",
    "args": [
        "run", "-i", "--rm",
        "-v", "${workspaceFolder}/.pongogo:/project/.pongogo:ro",
        "ghcr.io/pongogo/pongogo-server:latest"
    ]
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
PYTHON
    else
        # Create new config
        cat > "$CLAUDE_CONFIG" <<'JSON'
{
  "mcpServers": {
    "pongogo-knowledge": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${workspaceFolder}/.pongogo:/project/.pongogo:ro",
        "ghcr.io/pongogo/pongogo-server:latest"
      ]
    }
  }
}
JSON
    fi

    info "Pongogo installed successfully"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to pick up the configuration"
    echo "  2. Run 'pongogo init' in your project to create .pongogo/"
}

# Interactive menu when Docker not available
show_menu() {
    echo ""
    echo "Docker not detected. Choose an installation method:"
    echo ""
    echo "  1) Install Docker (recommended)"
    echo "  2) Install via pip (requires Python 3.10+)"
    echo "  3) Exit"
    echo ""
    read -p "Enter choice [1-3]: " choice

    case "$choice" in
        1)
            install_docker
            ;;
        2)
            install_pip
            ;;
        3)
            echo "Installation cancelled."
            exit 0
            ;;
        *)
            warn "Invalid choice. Please enter 1, 2, or 3."
            show_menu
            ;;
    esac
}

# Main installation flow
main() {
    echo "Pongogo Installation"
    echo "===================="
    echo ""

    detect_platform

    if has_docker; then
        install_docker_based
    else
        show_menu
    fi
}

main
