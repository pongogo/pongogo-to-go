"""E2E tests for slash command workflows.

Tests the explicit slash command interactions:
- /pongogo-retro: Retrospective flow
- /pongogo-log: Work log creation
- /pongogo-done: Completion checklist

Note: Requires Docker and mock MCP client (#376).
"""

import pytest

# Mark all tests as E2E (skip if Docker not available)
pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestRetroCommand:
    """Tests for /pongogo-retro command."""

    @pytest.mark.skip(reason="Requires mock MCP client (#376)")
    def test_retro_produces_structured_output(self, pongogo_server):
        """Running /pongogo-retro should produce structured retrospective."""
        # TODO: Implement when mock MCP client is available
        # Expected output should contain:
        # - What went well
        # - What could improve
        # - Action items
        pass


class TestLogCommand:
    """Tests for /pongogo-log command."""

    @pytest.mark.skip(reason="Requires mock MCP client (#376)")
    def test_log_creates_entry(self, pongogo_server):
        """Running /pongogo-log should guide work log creation."""
        # TODO: Implement when mock MCP client is available
        pass


class TestDoneCommand:
    """Tests for /pongogo-done command."""

    @pytest.mark.skip(reason="Requires mock MCP client (#376)")
    def test_done_shows_checklist(self, pongogo_server):
        """Running /pongogo-done should show completion checklist."""
        # TODO: Implement when mock MCP client is available
        pass
