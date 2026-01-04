"""Pongogo upgrade functionality.

Provides upgrade instructions for Docker installations.
Used by the upgrade_pongogo MCP tool.

Note: The MCP server runs INSIDE a Docker container, so it cannot execute
docker commands. Instead, we return instructions for the user to run on
their host machine.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class InstallMethod(Enum):
    """Installation method for Pongogo."""

    DOCKER = "docker"
    PIP = "pip"
    UNKNOWN = "unknown"


@dataclass
class UpgradeResult:
    """Result of an upgrade operation."""

    success: bool
    method: InstallMethod
    message: str
    current_version: str | None = None
    upgrade_command: str | None = None


def detect_install_method() -> InstallMethod:
    """Detect how Pongogo was installed.

    Checks for Docker container environment markers:
    - /.dockerenv file existence
    - /proc/1/cgroup containing docker

    Returns:
        InstallMethod indicating docker or pip.
    """
    # Check for Docker container markers
    if Path("/.dockerenv").exists():
        return InstallMethod.DOCKER

    try:
        with open("/proc/1/cgroup") as f:
            if "docker" in f.read():
                return InstallMethod.DOCKER
    except (FileNotFoundError, PermissionError):
        pass

    # Not in Docker - this is a development environment
    return InstallMethod.PIP


def get_current_version() -> str:
    """Get currently installed Pongogo version.

    Version detection order:
    1. PONGOGO_VERSION environment variable (set in Docker images)
    2. Package __version__ (fallback for development)

    Returns:
        Version string (e.g., "0.1.17", "vbeta-20260102-abc123")
    """
    # Docker images set PONGOGO_VERSION during build
    env_version = os.environ.get("PONGOGO_VERSION")
    if env_version:
        return env_version

    try:
        # Fallback to package version for development
        from mcp_server import __version__

        return __version__
    except ImportError:
        return "unknown"


def upgrade() -> UpgradeResult:
    """Get upgrade instructions for Pongogo.

    Since the MCP server runs inside a Docker container, we cannot execute
    docker commands from within. Instead, we return instructions for the
    user to run on their host machine.

    Returns:
        UpgradeResult with instructions for upgrading.
    """
    current = get_current_version()
    method = detect_install_method()

    if method == InstallMethod.DOCKER:
        # Inside Docker - provide instructions for host
        return UpgradeResult(
            success=True,
            method=InstallMethod.DOCKER,
            message=(
                "To upgrade Pongogo, run in your terminal:\n\n"
                "  docker pull ghcr.io/pongogo/pongogo-server:stable\n\n"
                "Then restart Claude Code to use the new version."
            ),
            current_version=current,
            upgrade_command="docker pull ghcr.io/pongogo/pongogo-server:stable",
        )
    elif method == InstallMethod.PIP:
        # Development environment - pip upgrade
        return UpgradeResult(
            success=True,
            method=InstallMethod.PIP,
            message=(
                "To upgrade Pongogo, run:\n\n"
                "  pip install --upgrade pongogo\n\n"
                "Then restart Claude Code to use the new version."
            ),
            current_version=current,
            upgrade_command="pip install --upgrade pongogo",
        )
    else:
        return UpgradeResult(
            success=False,
            method=InstallMethod.UNKNOWN,
            message="Could not detect installation method",
            current_version=current,
        )
