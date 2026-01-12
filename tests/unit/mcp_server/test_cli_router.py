"""Tests for CLI router entry point and formatter.

Related: Task #482, Sub-Task #487, Issue #517 (rubric-optimized formatter)
"""

from mcp_server.formatter import (
    _extract_evaluation_criteria,
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


class TestExtractEvaluationCriteria:
    """Tests for evaluation criteria extraction from frontmatter."""

    def test_extracts_success_signals(self):
        """Should extract success_signals from frontmatter."""
        content = """---
title: Test
evaluation:
  success_signals:
    - Signal one
    - Signal two
    - Signal three
  failure_signals:
    - Failure one
---

# Content
"""
        result = _extract_evaluation_criteria(content)
        assert len(result["success"]) == 3
        assert "Signal one" in result["success"]

    def test_extracts_failure_signals(self):
        """Should extract failure_signals from frontmatter."""
        content = """---
evaluation:
  success_signals:
    - Success
  failure_signals:
    - Failure one
    - Failure two
---
"""
        result = _extract_evaluation_criteria(content)
        assert len(result["failure"]) == 2
        assert "Failure one" in result["failure"]

    def test_limits_to_three_signals(self):
        """Should limit to 3 signals each."""
        content = """---
evaluation:
  success_signals:
    - One
    - Two
    - Three
    - Four
    - Five
  failure_signals:
    - A
    - B
    - C
    - D
---
"""
        result = _extract_evaluation_criteria(content)
        assert len(result["success"]) == 3
        assert len(result["failure"]) == 3

    def test_handles_missing_evaluation(self):
        """Should return empty lists if no evaluation section."""
        content = """---
title: No evaluation
---
"""
        result = _extract_evaluation_criteria(content)
        assert result["success"] == []
        assert result["failure"] == []

    def test_handles_no_frontmatter(self):
        """Should return empty lists if no frontmatter."""
        content = "# Just content"
        result = _extract_evaluation_criteria(content)
        assert result["success"] == []
        assert result["failure"] == []


class TestFormatRoutingResults:
    """Tests for routing result formatting (rubric-optimized XML format)."""

    def test_returns_empty_for_no_results(self):
        """Should return empty string when no relevant content."""
        result = format_routing_results({"instructions": [], "count": 0})
        assert result == ""

    def test_produces_xml_structure(self):
        """CRITICAL: Should produce XML-structured output (XML-1)."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:xml",
                    "category": "testing",
                    "description": "XML test",
                    "routing_score": 0.9,
                    "content": "Test content",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        # XML structure markers
        assert "<pongogo_routing" in result
        assert "</pongogo_routing>" in result
        assert "<directive>" in result
        assert "<instructions count=" in result
        assert "<instruction id=" in result
        assert "<expected_behavior>" in result

    def test_includes_directive(self):
        """Should include directive section (CLR-1)."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:directive",
                    "category": "testing",
                    "description": "Directive test",
                    "routing_score": 0.9,
                    "content": "Content",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert "<directive>" in result
        assert "MUST read and follow" in result

    def test_formats_guidance_action(self):
        """CRITICAL: Should include guidance_action in XML format."""
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

        assert '<action type="guidance_capture"' in result
        assert "MANDATORY" in result
        assert "log_user_guidance" in result
        assert "Always use TypeScript" in result
        assert "explicit" in result

    def test_formats_procedural_warning(self):
        """CRITICAL: Should include procedural_warning in XML format."""
        routing_result = {
            "instructions": [],
            "count": 0,
            "procedural_warning": {
                "warning": "Procedural instruction detected",
                "enforcement": "Read before executing",
            },
        }
        result = format_routing_results(routing_result)

        assert '<warning type="procedural">' in result
        assert "<enforcement>" in result
        assert "Read before executing" in result

    def test_formats_friction_risk_watch(self):
        """CRITICAL: Should include friction_risk_watch in XML format."""
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

        assert '<monitoring type="friction_risk">' in result
        assert "<guidance_type>" in result
        assert "<echo_detected>" in result

    def test_formats_instructions_with_metadata(self):
        """Should format instruction with all metadata."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:meta",
                    "category": "testing",
                    "description": "A test instruction",
                    "routing_score": 0.95,
                    "priority": "P1",
                    "file_path": "testing/test.instructions.md",
                    "content": "---\ntitle: Test\n---\n\n# Test Content\n\nBody here.",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert 'id="test:meta"' in result
        assert 'relevance="0.95"' in result
        assert 'priority="P1"' in result
        assert "<category>testing</category>" in result
        assert "<file>testing/test.instructions.md</file>" in result
        assert "<summary>A test instruction</summary>" in result
        assert "# Test Content" in result
        # Frontmatter should be stripped from content
        assert "title: Test" not in result

    def test_includes_compliance_criteria(self):
        """Should extract and include compliance_criteria from frontmatter."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:criteria",
                    "category": "testing",
                    "description": "Criteria test",
                    "routing_score": 0.9,
                    "content": """---
title: Test
evaluation:
  success_signals:
    - Success signal one
    - Success signal two
  failure_signals:
    - Failure signal one
---

# Content
""",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert "<compliance_criteria>" in result
        assert "<success>" in result
        assert "Success signal one" in result
        assert "<failure>" in result
        assert "Failure signal one" in result

    def test_truncates_long_content(self):
        """Should truncate content over 1500 chars."""
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
        assert "[...truncated]" in result
        # Should not have full 2000 chars (allow small buffer for edge cases)
        assert result.count("A") < 1600

    def test_includes_expected_behavior(self):
        """Should include expected_behavior section (COT-2, HALL-1)."""
        routing_result = {
            "instructions": [
                {
                    "id": "test:behavior",
                    "category": "testing",
                    "description": "Behavior test",
                    "routing_score": 0.9,
                    "content": "Content",
                }
            ],
            "count": 1,
        }
        result = format_routing_results(routing_result)

        assert "<expected_behavior>" in result
        assert "READ the instruction content" in result
        assert "ask the user rather than guessing" in result

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

        # Both should be present in XML structure
        assert '<action type="guidance_capture"' in result
        assert '<instructions count="1">' in result
        assert "<expected_behavior>" in result
