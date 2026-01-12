"""Verify the correct routing engine version is loaded.

This test catches import errors and misconfigurations that would
cause fallback to the baseline durian-00 engine.

Background:
    The routing system has a baseline "durian-00" engine that provides
    minimal functionality. When pongogo_router.py fails to import
    (due to path issues, missing dependencies, etc.), the system
    silently falls back to this baseline.

    This test ensures CI catches such regressions before they reach
    production. See PI-016 for the incident that motivated this test.

Note:
    The pongogo_router module must be imported for its engine to be
    registered. In production, this happens via MCP server startup.
    In tests, we explicitly import it to simulate that behavior.
"""

import pytest

# Import pongogo_router FIRST to ensure it registers itself.
# This simulates what happens in production when the MCP server starts.
# If this import fails, the test suite will fail immediately with
# a clear error message about what went wrong.
from mcp_server import pongogo_router  # noqa: F401 - import for side effects
from mcp_server.routing_engine import get_available_engines, get_default_engine

pytestmark = [pytest.mark.integration]


class TestRoutingEngineVersion:
    """Verify production routing engine is loaded, not baseline fallback."""

    def test_default_engine_is_not_baseline(self) -> None:
        """Default engine should NOT be the baseline fallback.

        If this test fails, it means pongogo_router.py failed to import
        and register itself. Check for:
        - Import path errors (mcp_server vs src.mcp_server)
        - Missing dependencies
        - Syntax errors in pongogo_router.py
        """
        default = get_default_engine()
        available = get_available_engines()

        assert default != "durian-00", (
            f"Default engine is baseline 'durian-00' - "
            f"this indicates an import error in pongogo_router.py. "
            f"Available engines: {available}"
        )

    def test_default_engine_is_durian_06_series(self) -> None:
        """Default engine should be the durian-0.6.x production series.

        The durian-0.6.x series is the current production routing engine.
        If this test fails with a different version, either:
        - A new version was released (update this test)
        - There's a configuration issue
        """
        default = get_default_engine()
        available = get_available_engines()

        assert default.startswith("durian-0.6"), (
            f"Expected durian-0.6.x series, got '{default}'. "
            f"Available engines: {available}. "
            f"If a new version was released, update this test."
        )

    def test_pongogo_router_module_loads(self) -> None:
        """pongogo_router module should import without errors.

        This import will fail if there are import path issues,
        missing dependencies, or syntax errors.
        """
        # This import will raise if there are issues
        from mcp_server import pongogo_router

        # Verify it has the expected version constant
        assert hasattr(
            pongogo_router, "DURIAN_VERSION"
        ), "pongogo_router missing DURIAN_VERSION constant"

        # Verify the version matches what we expect
        assert pongogo_router.DURIAN_VERSION.startswith("durian-0.6"), (
            f"pongogo_router.DURIAN_VERSION = '{pongogo_router.DURIAN_VERSION}' "
            f"does not match expected durian-0.6.x series"
        )

    def test_pongogo_router_registered_as_default(self) -> None:
        """pongogo_router should register itself as the default engine.

        The module sets itself as default at import time via:
        set_default_engine(DURIAN_VERSION)
        """

        default = get_default_engine()

        assert default == pongogo_router.DURIAN_VERSION, (
            f"Default engine '{default}' does not match "
            f"pongogo_router.DURIAN_VERSION '{pongogo_router.DURIAN_VERSION}'. "
            f"The pongogo_router module may not have called set_default_engine()."
        )

    def test_available_engines_includes_pongogo_router(self) -> None:
        """Available engines should include the pongogo router version."""

        available = get_available_engines()

        assert pongogo_router.DURIAN_VERSION in available, (
            f"pongogo_router.DURIAN_VERSION '{pongogo_router.DURIAN_VERSION}' "
            f"not in available engines: {available}. "
            f"The engine may not have been registered with @register_engine."
        )
