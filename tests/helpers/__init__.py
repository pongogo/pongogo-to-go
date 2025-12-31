"""Test helpers for pongogo-to-go.

This package provides utilities for testing the Pongogo MCP server:
- MockMCPClient: Programmatic MCP client for testing
- Assertions: Common assertion helpers
- Matchers: Response content matchers
"""

from .assertions import (
    assert_contains_instruction,
    assert_error_code,
    assert_routing_success,
    assert_tool_exists,
)
from .matchers import (
    CHECKLIST_MATCHER,
    LEARNING_LOOP_MATCHER,
    WORK_LOG_MATCHER,
    ContentMatcher,
)
from .mock_mcp_client import MCPResponse, MockMCPClient

__all__ = [
    # Client
    "MockMCPClient",
    "MCPResponse",
    # Assertions
    "assert_routing_success",
    "assert_contains_instruction",
    "assert_error_code",
    "assert_tool_exists",
    # Matchers
    "ContentMatcher",
    "LEARNING_LOOP_MATCHER",
    "WORK_LOG_MATCHER",
    "CHECKLIST_MATCHER",
]
