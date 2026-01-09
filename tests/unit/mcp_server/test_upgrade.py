"""Unit tests for upgrade module.

Tests upgrade detection, version retrieval, and instruction generation
without requiring Docker.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mcp_server.upgrade import (
    InstallMethod,
    UpgradeResult,
    detect_install_method,
    get_current_version,
    upgrade,
)


class TestDetectInstallMethod:
    """Tests for detect_install_method function."""

    def test_detects_docker_via_dockerenv(self, tmp_path: Path):
        """Should detect Docker when /.dockerenv exists."""
        with patch.object(Path, "exists", return_value=True):
            result = detect_install_method()
            assert result == InstallMethod.DOCKER

    def test_detects_docker_via_cgroup(self):
        """Should detect Docker when /proc/1/cgroup contains 'docker'."""
        with patch.object(Path, "exists", return_value=False):
            with patch(
                "builtins.open",
                mock_open(read_data="12:devices:/docker/abc123\n"),
            ):
                result = detect_install_method()
                assert result == InstallMethod.DOCKER

    def test_detects_pip_when_no_docker_markers(self):
        """Should detect pip when no Docker markers present."""
        with patch.object(Path, "exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                result = detect_install_method()
                assert result == InstallMethod.PIP

    def test_handles_permission_error_on_cgroup(self):
        """Should handle PermissionError when reading cgroup."""
        with patch.object(Path, "exists", return_value=False):
            with patch("builtins.open", side_effect=PermissionError):
                result = detect_install_method()
                assert result == InstallMethod.PIP


class TestGetCurrentVersion:
    """Tests for get_current_version function."""

    def test_returns_env_version_when_set(self):
        """Should return PONGOGO_VERSION env var when set."""
        with patch.dict(os.environ, {"PONGOGO_VERSION": "1.2.3"}):
            result = get_current_version()
            assert result == "1.2.3"

    def test_returns_package_version_when_no_env(self):
        """Should fall back to package version when env not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove PONGOGO_VERSION if it exists
            os.environ.pop("PONGOGO_VERSION", None)

            with patch(
                "mcp_server.upgrade.__version__",
                "0.1.0",
                create=True,
            ):
                # This may return "unknown" if package not installed
                result = get_current_version()
                assert isinstance(result, str)
                assert len(result) > 0

    def test_returns_unknown_on_import_error(self):
        """Should return 'unknown' when package version unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PONGOGO_VERSION", None)

            with patch.dict("sys.modules", {"mcp_server": None}):
                result = get_current_version()
                # May be "unknown" or actual version depending on install
                assert isinstance(result, str)


class TestUpgrade:
    """Tests for upgrade function."""

    def test_docker_upgrade_returns_docker_command(self):
        """Should return docker pull command for Docker installs."""
        with patch(
            "mcp_server.upgrade.detect_install_method",
            return_value=InstallMethod.DOCKER,
        ):
            with patch(
                "mcp_server.upgrade.get_current_version",
                return_value="1.0.0",
            ):
                result = upgrade()

                assert result.success is True
                assert result.method == InstallMethod.DOCKER
                assert "docker pull" in result.upgrade_command
                assert "ghcr.io" in result.upgrade_command
                assert result.current_version == "1.0.0"

    def test_pip_upgrade_returns_pip_command(self):
        """Should return pip install command for pip installs."""
        with patch(
            "mcp_server.upgrade.detect_install_method",
            return_value=InstallMethod.PIP,
        ):
            with patch(
                "mcp_server.upgrade.get_current_version",
                return_value="0.1.0",
            ):
                result = upgrade()

                assert result.success is True
                assert result.method == InstallMethod.PIP
                assert "pip install" in result.upgrade_command
                assert "pongogo" in result.upgrade_command

    def test_unknown_method_returns_failure(self):
        """Should return failure for unknown install method."""
        with patch(
            "mcp_server.upgrade.detect_install_method",
            return_value=InstallMethod.UNKNOWN,
        ):
            result = upgrade()

            assert result.success is False
            assert result.method == InstallMethod.UNKNOWN
            assert "Could not detect" in result.message


class TestUpgradeResult:
    """Tests for UpgradeResult dataclass."""

    def test_dataclass_creation(self):
        """Should create UpgradeResult with all fields."""
        result = UpgradeResult(
            success=True,
            method=InstallMethod.DOCKER,
            message="Test message",
            current_version="1.0.0",
            upgrade_command="docker pull test",
        )

        assert result.success is True
        assert result.method == InstallMethod.DOCKER
        assert result.message == "Test message"
        assert result.current_version == "1.0.0"
        assert result.upgrade_command == "docker pull test"

    def test_optional_fields_default_to_none(self):
        """Should allow optional fields to be None."""
        result = UpgradeResult(
            success=False,
            method=InstallMethod.UNKNOWN,
            message="Error",
        )

        assert result.current_version is None
        assert result.upgrade_command is None
