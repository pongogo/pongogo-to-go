"""Response matchers for flexible assertions.

This module provides pattern-based matchers for MCP response content,
allowing flexible validation of response content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from re import Pattern
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_mcp_client import MCPResponse


@dataclass
class ContentMatcher:
    """Matcher for MCP response content.

    Supports both string matching and regex patterns.

    Usage:
        matcher = ContentMatcher(patterns=["learning loop", "retrospective"])
        if matcher.matches(response):
            print("Match found!")

        # Or use assert_matches for test assertions
        matcher.assert_matches(response)

    Attributes:
        patterns: List of strings or compiled regex patterns
        case_sensitive: Whether string matching is case-sensitive
    """

    patterns: list[Pattern[str] | str] = field(default_factory=list)
    case_sensitive: bool = False

    def matches(self, response: MCPResponse) -> bool:
        """Check if response content matches all patterns.

        Args:
            response: MCP response to check

        Returns:
            True if all patterns match, False otherwise
        """
        if not response.success or not response.content:
            return False

        content = response.content
        if not self.case_sensitive:
            content = content.lower()

        for pattern in self.patterns:
            if isinstance(pattern, str):
                check = pattern if self.case_sensitive else pattern.lower()
                if check not in content:
                    return False
            else:
                # Compiled regex pattern
                search_content = response.content if self.case_sensitive else content
                if not pattern.search(search_content):
                    return False

        return True

    def assert_matches(self, response: MCPResponse) -> None:
        """Assert response matches, with helpful error message.

        Args:
            response: MCP response to validate

        Raises:
            AssertionError: If response doesn't match patterns
        """
        assert response.success, f"Response failed: {response.error_message}"
        assert response.content, "No content in response"

        content = response.content
        if not self.case_sensitive:
            content = content.lower()

        for pattern in self.patterns:
            if isinstance(pattern, str):
                check = pattern if self.case_sensitive else pattern.lower()
                assert (
                    check in content
                ), f"Expected '{pattern}' in content. Got: {response.content[:200]}..."
            else:
                # Compiled regex pattern
                search_content = response.content if self.case_sensitive else content
                assert pattern.search(
                    search_content
                ), f"Pattern {pattern.pattern} not found in content"

    def __and__(self, other: ContentMatcher) -> ContentMatcher:
        """Combine two matchers with AND logic.

        Args:
            other: Another matcher to combine with

        Returns:
            New matcher requiring all patterns from both
        """
        return ContentMatcher(
            patterns=self.patterns + other.patterns,
            case_sensitive=self.case_sensitive or other.case_sensitive,
        )

    def __or__(self, other: ContentMatcher) -> AnyMatcher:
        """Combine two matchers with OR logic.

        Args:
            other: Another matcher to combine with

        Returns:
            AnyMatcher that matches if either matcher matches
        """
        return AnyMatcher(matchers=[self, other])


@dataclass
class AnyMatcher:
    """Matcher that succeeds if ANY sub-matcher matches.

    Useful for testing multiple valid responses.
    """

    matchers: list[ContentMatcher] = field(default_factory=list)

    def matches(self, response: MCPResponse) -> bool:
        """Check if any sub-matcher matches.

        Args:
            response: MCP response to check

        Returns:
            True if any matcher matches, False if none match
        """
        return any(m.matches(response) for m in self.matchers)

    def assert_matches(self, response: MCPResponse) -> None:
        """Assert at least one matcher matches.

        Args:
            response: MCP response to validate

        Raises:
            AssertionError: If no matcher matches
        """
        assert response.success, f"Response failed: {response.error_message}"

        if not self.matches(response):
            pattern_strs = [str(m.patterns) for m in self.matchers]
            raise AssertionError(
                f"None of the expected patterns matched: {pattern_strs}. "
                f"Got: {response.content[:200] if response.content else 'None'}..."
            )


# =============================================================================
# Pre-built Matchers for Common Scenarios
# =============================================================================

# Learning and reflection patterns
LEARNING_LOOP_MATCHER = ContentMatcher(
    patterns=["learning loop", "retrospective"],
    case_sensitive=False,
)

RETROSPECTIVE_MATCHER = ContentMatcher(
    patterns=["what went well", "what could improve"],
    case_sensitive=False,
)

# Work tracking patterns
WORK_LOG_MATCHER = ContentMatcher(
    patterns=["work log", "entry"],
    case_sensitive=False,
)

CHECKLIST_MATCHER = ContentMatcher(
    patterns=["checklist"],
    case_sensitive=False,
)

# Issue management patterns
ISSUE_CLOSURE_MATCHER = ContentMatcher(
    patterns=["closure", "issue"],
    case_sensitive=False,
)

ISSUE_COMMENCEMENT_MATCHER = ContentMatcher(
    patterns=["commencement", "prerequisites"],
    case_sensitive=False,
)

# Routing patterns
ROUTING_SUCCESS_MATCHER = ContentMatcher(
    patterns=["instruction", "found"],
    case_sensitive=False,
)

NO_RESULTS_MATCHER = ContentMatcher(
    patterns=["no instruction", "not found"],
    case_sensitive=False,
)


# =============================================================================
# Regex-based Matchers
# =============================================================================


def regex_matcher(*patterns: str, case_sensitive: bool = False) -> ContentMatcher:
    """Create a matcher from regex patterns.

    Args:
        *patterns: Regex pattern strings
        case_sensitive: Whether to match case

    Returns:
        ContentMatcher with compiled regex patterns
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = [re.compile(p, flags) for p in patterns]
    return ContentMatcher(patterns=compiled, case_sensitive=case_sensitive)


# Version pattern: matches "v1.2.3" or "durian-0.6" style versions
VERSION_MATCHER = regex_matcher(r"\b(v?\d+\.\d+(\.\d+)?|durian-\d+\.\d+)\b")

# Instruction file pattern: matches "*.instructions.md" references
INSTRUCTION_FILE_MATCHER = regex_matcher(r"\w+\.instructions\.md")
