"""Tests for CLI router entry point and formatter.

Related: Task #482, Sub-Task #487
"""

from mcp_server.formatter import (
    extract_content_without_frontmatter,
    format_routing_results,
)


class TestExtractContentWithoutFrontmatter:
    """Tests for frontmatter extraction."""

    def test_removes_yaml_frontmatter(self):
        """Should strip YAML frontmatter from content."""
        content = """---
title: Test Instruction
description: A test
---

# Actual Content

This is the body.
"""
        result = extract_content_without_frontmatter(content)
        assert result.strip().startswith("# Actual Content")
        assert "title:" not in result
        assert "---" not in result.strip()[:10]

    def test_handles_content_without_frontmatter(self):
        """Should return content unchanged if no frontmatter."""
        content = "# Just Content\n\nNo frontmatter here."
        result = extract_content_without_frontmatter(content)
        assert result == content

    def test_handles_empty_content(self):
        """Should handle empty content."""
        result = extract_content_without_frontmatter("")
        assert result == ""


class TestFormatRoutingResults:
    """Tests for routing result formatting."""

    def test_returns_empty_for_no_results(self):
        """Should return empty string when no relevant content."""
        result = format_routing_results({"instructions": [], "count": 0})
        assert result == ""

    def test_formats_guidance_action(self):
        """CRITICAL: Should include guidance_action in output."""
        routing_result = {
            "instructions": [],
            "count": 0,
            "guidance_action": {
                "action": "log_user_guidance",
                "directive": "USER GUIDANCE DETECTED - Call log_user_guidance() MCP tool",
                "parameters": {
                    "content": "Always use TypeScript",
                    "guidance_type": "explicit",
                    "context": "user preference",
                },
                "rationale": "User expressed behavioral rule",
            },
        }
        result = format_routing_results(routing_result)

        assert "ACTION REQUIRED" in result
        assert "log_user_guidance" in result
        assert "Always use TypeScript" in result
        assert "explicit" in result

    def test_formats_procedural_warning(self):
        """CRITICAL: Should include procedural_warning in output."""
        routing_result = {
            "instructions": [],
            "count": 0,
            "procedural_warning": {
                "warning": "Procedural instruction detected",
                "enforcement": "Read before executing",
            },
        }
        result = format_routing_results(routing_result)

        assert "PROCEDURAL INSTRUCTION WARNING" in result
        assert "Read before executing" in result

    def test_formats_friction_risk_watch(self):
        """CRITICAL: Should include friction_risk_watch in output when enabled with context."""
        # friction_risk_watch only appears when there's other content
        routing_result = {
            "instructions": [
                {
                    "id": "test:friction",
                    "category": "testing",
                    "description": "Friction test",
                    "routing_score": 0.9,
                    "content": "Content",
                }
            ],
            "count": 1,
            "friction_risk_watch": {
                "enabled": True,
                "guidance_type": "explicit",
                "echo_detected": False,
                "frustration_level": "low",
            },
        }
        result = format_routing_results(routing_result)

        assert "Friction Risk Watch Active" in result
        assert "Guidance Type" in result
        assert "Echo Detected" in result

    def test_formats_instructions(self):
        """Should format instruction list correctly."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:instruction",
                    "category": "testing",
                    "description": "A test instruction",
                    "routing_score": 0.95,
                    "file_path": "testing/test.instructions.md",
                    "content": "---\ntitle: Test\n---\n\n# Test Content\n\nBody here.",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert "Relevant Pongogo Instructions" in result
        assert "test:instruction" in result
        assert "testing" in result
        assert "0.95" in result
        assert "# Test Content" in result
        # Frontmatter should be stripped
        assert "title: Test" not in result

    def test_truncates_long_content(self):
        """Should truncate content over 1000 chars."""
        long_content = "A" * 2000
        routing_result = {
            "instructions": [
                {
                    "id": "test:long",
                    "category": "testing",
                    "description": "Long content test",
                    "routing_score": 0.9,
                    "content": long_content,
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        # Should have truncation marker
        assert "..." in result
        # Should not have full 2000 chars
        assert result.count("A") <= 1000

    def test_includes_footer(self):
        """Should include footer note."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:footer",
                    "category": "testing",
                    "description": "Footer test",
                    "routing_score": 0.9,
                    "content": "Content",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert "automatically discovered" in result.lower()

    def test_combined_guidance_and_instructions(self):
        """Should format both guidance_action and instructions together."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:combined",
                    "category": "testing",
                    "description": "Combined test",
                    "routing_score": 0.85,
                    "content": "Test content",
                }
            ],
            "count": 1,
            "guidance_action": {
                "directive": "USER GUIDANCE DETECTED",
                "parameters": {"content": "Test guidance"},
                "rationale": "Test",
            },
        }
        result = format_routing_results(routing_result)

        # Both should be present
        assert "ACTION REQUIRED" in result
        assert "Relevant Pongogo Instructions" in result
