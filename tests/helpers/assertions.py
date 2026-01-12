"""Assertion helpers for MCP response validation.

This module provides common assertions for testing MCP responses,
with clear error messages to aid debugging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_mcp_client import MCPResponse


def assert_routing_success(response: MCPResponse) -> None:
    """Assert that routing returned valid instructions.

    Args:
        response: MCP response to validate

    Raises:
        AssertionError: If routing failed or returned empty content
    """
    assert response.success, f"Routing failed: {response.error_message}"
    assert response.content, "No content in response"
    assert len(response.content) > 0, "Empty content in response"


def assert_contains_instruction(
    response: MCPResponse,
    instruction_name: str,
) -> None:
    """Assert response contains a specific instruction.

    Args:
        response: MCP response to check
        instruction_name: Name or partial name to look for

    Raises:
        AssertionError: If instruction not found in response
    """
    assert response.success, f"Request failed: {response.error_message}"
    assert response.content, "No content in response"
    assert instruction_name in response.content, (
        f"Expected '{instruction_name}' in response. Got: {response.content[:200]}..."
    )


def assert_error_code(
    response: MCPResponse,
    expected_code: int,
) -> None:
    """Assert response has specific error code.

    Args:
        response: MCP response to check
        expected_code: Expected JSON-RPC error code

    Raises:
        AssertionError: If response is success or has different error code
    """
    assert not response.success, "Expected error response, got success"
    assert response.error_code == expected_code, (
        f"Expected error code {expected_code}, got {response.error_code}"
    )


def assert_tool_exists(tools: list[dict], tool_name: str) -> None:
    """Assert tool exists in tools list.

    Args:
        tools: List of tool definitions from list_tools()
        tool_name: Name of tool to find

    Raises:
        AssertionError: If tool not found
    """
    tool_names = [t.get("name", "") for t in tools]
    assert tool_name in tool_names, (
        f"Tool '{tool_name}' not found. Available: {tool_names}"
    )


def assert_response_contains(
    response: MCPResponse,
    *substrings: str,
    case_sensitive: bool = False,
) -> None:
    """Assert response content contains all specified substrings.

    Args:
        response: MCP response to check
        *substrings: Strings that must be present in content
        case_sensitive: Whether to match case (default: False)

    Raises:
        AssertionError: If any substring not found
    """
    assert response.success, f"Request failed: {response.error_message}"
    assert response.content, "No content in response"

    content = response.content if case_sensitive else response.content.lower()

    for substring in substrings:
        check = substring if case_sensitive else substring.lower()
        assert check in content, (
            f"Expected '{substring}' in content. Got: {response.content[:200]}..."
        )


def assert_response_not_contains(
    response: MCPResponse,
    *substrings: str,
    case_sensitive: bool = False,
) -> None:
    """Assert response content does NOT contain specified substrings.

    Args:
        response: MCP response to check
        *substrings: Strings that must NOT be present in content
        case_sensitive: Whether to match case (default: False)

    Raises:
        AssertionError: If any substring is found
    """
    assert response.success, f"Request failed: {response.error_message}"

    if not response.content:
        return  # No content means nothing to check

    content = response.content if case_sensitive else response.content.lower()

    for substring in substrings:
        check = substring if case_sensitive else substring.lower()
        assert check not in content, f"Unexpected '{substring}' found in content"
