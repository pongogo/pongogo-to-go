"""Pongogo upgrade functionality.

Provides upgrade instructions and version checking for Docker installations.
Used by the upgrade_pongogo and check_for_updates MCP tools.

Note: The MCP server runs INSIDE a Docker container, so it cannot execute
docker commands. Instead, we return instructions for the user to run on
their host machine.
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache for version check results (1 hour TTL)
_version_cache: dict = {"latest": None, "timestamp": 0}
VERSION_CACHE_TTL = 3600  # 1 hour in seconds

# GitHub releases API endpoint
GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/pongogo/pongogo-to-go/releases/latest"
)


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


@dataclass
class VersionCheckResult:
    """Result of a version check operation."""

    current_version: str
    latest_version: str | None
    update_available: bool
    check_failed: bool = False
    error_message: str | None = None
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


def _normalize_version(version: str) -> str:
    """Normalize version string for comparison.

    Handles formats like:
    - "0.1.17"
    - "v0.1.17"
    - "vbeta-20260102-abc123"

    Returns:
        Normalized version string (strips leading 'v').
    """
    if version.startswith("v"):
        return version[1:]
    return version


def _parse_semver(version: str) -> tuple[int, int, int] | None:
    """Parse semantic version string into tuple.

    Args:
        version: Version string like "0.1.17" or "1.2.3"

    Returns:
        Tuple of (major, minor, patch) or None if not semver.
    """
    normalized = _normalize_version(version)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", normalized)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None


def _is_newer_version(current: str, latest: str) -> bool:
    """Check if latest version is newer than current.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest is newer than current.
    """
    current_parts = _parse_semver(current)
    latest_parts = _parse_semver(latest)

    if current_parts is None or latest_parts is None:
        # Can't compare non-semver versions, assume no update
        return False

    return latest_parts > current_parts


def fetch_latest_version() -> str | None:
    """Fetch latest version from GitHub releases API.

    Uses caching to avoid rate limiting (1 hour TTL).

    Returns:
        Latest version string or None if fetch failed.
    """
    global _version_cache

    # Check cache
    now = time.time()
    if (
        _version_cache["latest"]
        and (now - _version_cache["timestamp"]) < VERSION_CACHE_TTL
    ):
        logger.debug("Using cached version info")
        return _version_cache["latest"]

    try:
        request = urllib.request.Request(
            GITHUB_RELEASES_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "pongogo-server",
            },
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            tag_name = data.get("tag_name")

            if tag_name:
                # Update cache
                _version_cache["latest"] = tag_name
                _version_cache["timestamp"] = now
                logger.debug(f"Fetched latest version: {tag_name}")
                return tag_name

    except urllib.error.URLError as e:
        logger.debug(f"Failed to fetch latest version (network): {e}")
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse releases response: {e}")
    except Exception as e:
        logger.debug(f"Unexpected error fetching version: {e}")

    return None


def check_for_updates() -> VersionCheckResult:
    """Check if a newer version of Pongogo is available.

    Fetches current version and compares against latest GitHub release.
    Uses caching to avoid rate limiting.

    Returns:
        VersionCheckResult with version comparison info.
    """
    current = get_current_version()
    method = detect_install_method()

    # Determine upgrade command based on install method
    if method == InstallMethod.DOCKER:
        upgrade_cmd = "docker pull ghcr.io/pongogo/pongogo-server:stable"
    elif method == InstallMethod.PIP:
        upgrade_cmd = "pip install --upgrade pongogo"
    else:
        upgrade_cmd = None

    # Fetch latest version
    latest = fetch_latest_version()

    if latest is None:
        return VersionCheckResult(
            current_version=current,
            latest_version=None,
            update_available=False,
            check_failed=True,
            error_message="Could not fetch latest version (offline or rate limited)",
            upgrade_command=upgrade_cmd,
        )

    update_available = _is_newer_version(current, latest)

    return VersionCheckResult(
        current_version=current,
        latest_version=latest,
        update_available=update_available,
        check_failed=False,
        upgrade_command=upgrade_cmd if update_available else None,
    )
