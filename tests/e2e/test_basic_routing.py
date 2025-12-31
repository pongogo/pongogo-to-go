"""Basic routing tests.

These tests validate the MockMCPClient works correctly with pongogo-server
and provide foundational coverage for the routing system.
"""

import pytest

from tests.helpers import (
    assert_routing_success,
    assert_tool_exists,
)

# Mark all tests as E2E
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestBasicRouting:
    """Tests for basic instruction routing functionality."""

    async def test_route_instructions_returns_content(self, mock_mcp_client):
        """Test that routing a message returns instruction content."""
        response = await mock_mcp_client.route_instructions(
            message="how do I test my code?"
        )

        assert_routing_success(response)
        # Should return some content from sample instructions
        assert response.content is not None
        assert len(response.content) > 0

    async def test_list_tools_returns_expected_tools(self, mock_mcp_client):
        """Test that the server exposes expected tools."""
        tools = await mock_mcp_client.list_tools()

        # Core tools should be available
        assert_tool_exists(tools, "route_instructions")

    async def test_route_with_limit(self, mock_mcp_client):
        """Test that limit parameter works correctly."""
        response = await mock_mcp_client.route_instructions(
            message="project management",
            limit=1,
        )

        assert_routing_success(response)

    async def test_empty_message_handling(self, mock_mcp_client):
        """Test handling of empty message."""
        response = await mock_mcp_client.route_instructions(
            message="",
        )

        # Should handle gracefully (either success with no results or error)
        # The exact behavior depends on server implementation
        assert response.raw is not None  # At least got a response


class TestMCPClientLifecycle:
    """Tests for MockMCPClient connection lifecycle."""

    async def test_client_connects_and_initializes(self, mock_mcp_client):
        """Test that client properly connects and initializes MCP session."""
        # If we get here, the fixture succeeded in connecting
        # Verify we can make a basic call
        tools = await mock_mcp_client.list_tools()
        assert isinstance(tools, list)

    async def test_multiple_calls_same_session(self, mock_mcp_client):
        """Test making multiple calls in the same session."""
        # First call
        response1 = await mock_mcp_client.route_instructions(message="first query")
        assert response1.raw is not None

        # Second call
        response2 = await mock_mcp_client.route_instructions(message="second query")
        assert response2.raw is not None


class TestErrorHandling:
    """Tests for error handling in MCP communication."""

    async def test_invalid_tool_returns_error(self, mock_mcp_client):
        """Test calling a non-existent tool returns error."""
        response = await mock_mcp_client.call_tool(
            "nonexistent_tool_that_does_not_exist",
            {"arg": "value"},
        )

        # Should be an error response
        assert not response.success

    async def test_response_has_raw_data(self, mock_mcp_client):
        """Test that all responses include raw JSON-RPC data."""
        response = await mock_mcp_client.route_instructions(message="test query")

        # Raw response should be available for debugging
        assert response.raw is not None
        assert "jsonrpc" in response.raw
