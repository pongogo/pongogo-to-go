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

# Note: Direct pip installation is not yet supported for MCP server setup
# because Claude Code's ${workspaceFolder} expansion in the env section
# is unverified. Docker volume mounts are the only verified method for
# multi-repo isolation. See: https://github.com/pongogo/pongogo-to-go/issues/1

# Check if pip is available (needed for pongogo CLI)
check_pip() {
    if command -v pip3 &> /dev/null; then
        return 0
    elif command -v pip &> /dev/null; then
        return 0
    fi
    return 1
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v lsb_release &> /dev/null; then
        lsb_release -si | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

# Show pip installation instructions based on distro
show_pip_install_instructions() {
    local distro="$1"

    echo ""
    warn "pip is not installed. The pongogo CLI requires pip to install."
    echo ""
    echo "To install pip for your system:"
    echo ""

    case "$distro" in
        fedora|rhel|centos|rocky|alma)
            # Red Hat based
            echo "  ${GREEN}# Red Hat/Fedora:${NC}"
            echo "  sudo dnf install python3-pip"
            echo ""
            echo "  ${GREEN}# Or install rich directly (optional, for colored output):${NC}"
            echo "  sudo dnf install python3-rich"
            ;;
        debian|ubuntu|linuxmint|pop)
            # Debian based
            echo "  ${GREEN}# Debian/Ubuntu:${NC}"
            echo "  sudo apt update && sudo apt install python3-pip"
            ;;
        arch|manjaro|endeavouros)
            # Arch based
            echo "  ${GREEN}# Arch Linux:${NC}"
            echo "  sudo pacman -S python-pip"
            ;;
        opensuse*|suse*)
            # SUSE based
            echo "  ${GREEN}# openSUSE:${NC}"
            echo "  sudo zypper install python3-pip"
            ;;
        alpine)
            echo "  ${GREEN}# Alpine Linux:${NC}"
            echo "  sudo apk add py3-pip"
            ;;
        *)
            echo "  ${GREEN}# Generic Linux:${NC}"
            echo "  # Check your distribution's package manager for python3-pip"
            echo "  # Common package names: python3-pip, python-pip, py3-pip"
            ;;
    esac

    echo ""
    echo "After installing pip, run this script again."
    echo ""
}

# Install pongogo CLI via pip
install_pongogo_cli() {
    info "Installing Pongogo CLI..."

    # Use pip3 if available, otherwise pip
    local pip_cmd="pip3"
    if ! command -v pip3 &> /dev/null; then
        pip_cmd="pip"
    fi

    # Install pongogo package
    if $pip_cmd install --user pongogo 2>/dev/null; then
        info "Pongogo CLI installed successfully"
        return 0
    else
        # Try without --user if that fails (some systems don't allow --user)
        if $pip_cmd install pongogo 2>/dev/null; then
            info "Pongogo CLI installed successfully"
            return 0
        fi
    fi

    error "Failed to install Pongogo CLI via pip"
    return 1
}

# Docker-based installation
install_docker_based() {
    # Check if image already exists locally
    image_existed=false
    if docker image inspect pongogo.azurecr.io/pongogo:stable &>/dev/null; then
        image_existed=true
        info "Checking for updates..."
    else
        info "Downloading Pongogo Docker image..."
    fi

    # Capture docker pull output to show friendlier message
    # Use --quiet to suppress Docker's live progress output
    pull_output=$(docker pull --quiet pongogo.azurecr.io/pongogo:stable 2>&1)
    pull_exit_code=$?

    if [ $pull_exit_code -ne 0 ]; then
        error "Failed to pull Docker image: $pull_output"
    fi

    # Parse Docker's output to show appropriate message
    if echo "$pull_output" | grep -q "Image is up to date"; then
        info "Docker image is up to date"
    elif [ "$image_existed" = true ]; then
        info "Updated to latest Docker image"
    else
        info "Docker image downloaded"
    fi

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
        "pongogo.azurecr.io/pongogo:stable"
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
        "pongogo.azurecr.io/pongogo:stable"
      ]
    }
  }
}
JSON
    fi

    info "MCP server configured successfully"
    echo ""

    # Check for pip and install CLI
    local cli_installed=false
    if check_pip; then
        if install_pongogo_cli; then
            cli_installed=true
        fi
    else
        # Show platform-specific pip installation instructions
        case "$PLATFORM" in
            macos)
                echo ""
                warn "pip not found. To install the Pongogo CLI:"
                echo ""
                echo "  ${GREEN}# macOS (via Homebrew):${NC}"
                echo "  brew install python3"
                echo ""
                echo "  ${GREEN}# Then install pongogo:${NC}"
                echo "  pip3 install pongogo"
                ;;
            wsl)
                echo ""
                warn "pip not found. To install the Pongogo CLI:"
                echo ""
                echo "  ${GREEN}# WSL (Debian/Ubuntu):${NC}"
                echo "  sudo apt update && sudo apt install python3-pip"
                echo ""
                echo "  ${GREEN}# Then install pongogo:${NC}"
                echo "  pip3 install pongogo"
                ;;
            linux)
                distro=$(detect_distro)
                show_pip_install_instructions "$distro"
                echo "  ${GREEN}# Then install pongogo:${NC}"
                echo "  pip3 install pongogo"
                ;;
        esac
    fi

    echo ""
    info "Pongogo installation complete"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code to pick up the configuration"
    if [ "$cli_installed" = true ]; then
        echo "  2. Run 'pongogo init' in your project to create .pongogo/"
    else
        echo "  2. Install pip (see above), then run: pip3 install pongogo"
        echo "  3. Run 'pongogo init' in your project to create .pongogo/"
    fi
    echo ""
    echo "Check for updates periodically:"
    echo "  /pongogo-status   - shows version and update availability"
    echo "  /pongogo-diagnose - includes full version comparison"
}

# Menu when Docker not available
show_menu() {
    echo ""
    echo "Docker is required for Pongogo MCP server."
    echo ""
    echo "Docker ensures proper isolation when using Pongogo across"
    echo "multiple repositories on the same machine."
    echo ""
    echo "  1) Install Docker"
    echo "  2) Exit"
    echo ""
    read -p "Enter choice [1-2]: " choice

    case "$choice" in
        1)
            install_docker
            ;;
        2)
            echo "Installation cancelled."
            echo ""
            echo "To install Docker manually:"
            echo "  macOS:   brew install --cask docker"
            echo "  Linux:   https://docs.docker.com/engine/install/"
            echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
            exit 0
            ;;
        *)
            warn "Invalid choice. Please enter 1 or 2."
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
