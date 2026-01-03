"""Pongogo upgrade functionality.

Provides upgrade capabilities for Docker installations.
Used by the upgrade_pongogo MCP tool.

Note: Docker is currently the only supported method for MCP server deployment.
The pip upgrade code is retained for development use (editable installs) and
future support once multi-repo isolation is verified for direct Python installs.
See: https://github.com/pongogo/pongogo-to-go/issues/1
"""

import logging
import subprocess
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
    previous_version: str | None = None
    new_version: str | None = None


def detect_install_method() -> InstallMethod:
    """Detect how Pongogo was installed.

    Checks for Docker container environment markers:
    - /.dockerenv file existence
    - /proc/1/cgroup containing docker

    In production, this should always detect Docker since Docker is required
    for MCP server deployment. The PIP fallback is only for development
    environments (editable installs).

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

    # Not in Docker - this is a development environment (editable install)
    return InstallMethod.PIP


def get_current_version() -> str:
    """Get currently installed Pongogo version.

    Version detection order:
    1. PONGOGO_VERSION environment variable (set in Docker images)
    2. Package __version__ (fallback for development)

    Returns:
        Version string (e.g., "0.1.16", "vbeta-20260102-abc123")
    """
    import os

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


def upgrade_docker() -> UpgradeResult:
    """Upgrade Pongogo Docker image.

    Pulls the latest image from ghcr.io/pongogo/pongogo-server.

    Note: This only pulls the image. The container will use the new
    image on next restart (when user exits and re-enters Claude Code).
    """
    previous = get_current_version()

    try:
        result = subprocess.run(
            ["docker", "pull", "ghcr.io/pongogo/pongogo-server:latest"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return UpgradeResult(
                success=True,
                method=InstallMethod.DOCKER,
                message="Docker image updated. Restart Claude Code to use new version.",
                previous_version=previous,
            )
        else:
            return UpgradeResult(
                success=False,
                method=InstallMethod.DOCKER,
                message=f"Docker pull failed: {result.stderr}",
                previous_version=previous,
            )
    except subprocess.TimeoutExpired:
        return UpgradeResult(
            success=False,
            method=InstallMethod.DOCKER,
            message="Docker pull timed out",
            previous_version=previous,
        )
    except FileNotFoundError:
        return UpgradeResult(
            success=False,
            method=InstallMethod.DOCKER,
            message="Docker not found",
            previous_version=previous,
        )


def upgrade_pip() -> UpgradeResult:
    """Upgrade Pongogo via pip (development environments only).

    Uses pip install --upgrade pongogo to get latest version.

    Note: This is only used in development environments (editable installs).
    Production deployments use Docker and should never hit this path.
    """
    previous = get_current_version()

    try:
        result = subprocess.run(
            ["pip", "install", "--upgrade", "pongogo"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            # Check new version
            new_version = get_current_version()
            return UpgradeResult(
                success=True,
                method=InstallMethod.PIP,
                message="Pongogo upgraded. Restart Claude Code to use new version.",
                previous_version=previous,
                new_version=new_version,
            )
        else:
            return UpgradeResult(
                success=False,
                method=InstallMethod.PIP,
                message=f"pip upgrade failed: {result.stderr}",
                previous_version=previous,
            )
    except subprocess.TimeoutExpired:
        return UpgradeResult(
            success=False,
            method=InstallMethod.PIP,
            message="pip upgrade timed out",
            previous_version=previous,
        )
    except FileNotFoundError:
        return UpgradeResult(
            success=False,
            method=InstallMethod.PIP,
            message="pip not found",
            previous_version=previous,
        )


def upgrade() -> UpgradeResult:
    """Upgrade Pongogo using detected installation method.

    In production (Docker), pulls the latest image. In development
    environments (editable pip installs), upgrades via pip.

    Returns:
        UpgradeResult with status and message.
    """
    method = detect_install_method()

    if method == InstallMethod.DOCKER:
        return upgrade_docker()
    elif method == InstallMethod.PIP:
        return upgrade_pip()
    else:
        return UpgradeResult(
            success=False,
            method=InstallMethod.UNKNOWN,
            message="Could not detect installation method",
        )
