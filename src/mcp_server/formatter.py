"""
Routing Result Formatter for Pongogo-to-Go.

Formats routing results for Claude consumption via UserPromptSubmit hook.

RUBRIC-OPTIMIZED (Issue #517):
This formatter produces output optimized against the Claude Prompt Engineering
Rubric for maximum compliance. Key rubric alignments:
- XML-1/XML-2: XML tags for structure and separation
- CLR-1/CLR-2: Explicit directive + success/failure criteria
- COT-2: Expected behavior guides reasoning
- HALL-1: Permission to ask rather than guess

CRITICAL: This formatter includes ALL action directives, not just instructions.
- guidance_action: Tells Claude to call log_user_guidance()
- procedural_warning: Warns about procedural instructions
- friction_risk_watch: Signals for friction detection

Related: Task #482, Sub-Task #485, Issue #517
"""

import json
import re
from typing import Any


def extract_content_without_frontmatter(content: str) -> str:
    """
    Extract instruction content without YAML frontmatter.

    Args:
        content: Full instruction file content

    Returns:
        Content with frontmatter stripped
    """
    # Match YAML frontmatter (--- at start, --- to close)
    frontmatter_pattern = r"^---\s*\n.*?\n---\s*\n"
    return re.sub(frontmatter_pattern, "", content, flags=re.DOTALL)


def _extract_evaluation_criteria(content: str) -> dict[str, list[str]]:
    """
    Extract evaluation criteria from instruction content if present.

    Looks for success_signals and failure_signals in YAML frontmatter.

    Args:
        content: Full instruction file content

    Returns:
        Dict with 'success' and 'failure' lists, empty if not found
    """
    criteria: dict[str, list[str]] = {"success": [], "failure": []}

    # Try to extract from YAML frontmatter
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        return criteria

    frontmatter = frontmatter_match.group(1)

    # Extract success_signals
    success_match = re.search(r"success_signals:\s*\n((?:\s+-[^\n]+\n?)+)", frontmatter)
    if success_match:
        signals = re.findall(r"-\s*(.+)", success_match.group(1))
        criteria["success"] = [s.strip() for s in signals[:3]]  # Limit to 3

    # Extract failure_signals
    failure_match = re.search(r"failure_signals:\s*\n((?:\s+-[^\n]+\n?)+)", frontmatter)
    if failure_match:
        signals = re.findall(r"-\s*(.+)", failure_match.group(1))
        criteria["failure"] = [s.strip() for s in signals[:3]]  # Limit to 3

    return criteria


def format_routing_results(
    routing_result: dict[str, Any],
    message: str = "",
    enable_auto_read: bool = True,
) -> str:
    """
    Format routing results for Claude consumption via hook.

    RUBRIC-OPTIMIZED: Produces XML-structured output with compliance criteria
    and expected behavior guidance for maximum Claude compliance.

    Args:
        routing_result: Results from router.route() call
        message: Original user message (for context)
        enable_auto_read: If True, include auto-read instructions

    Returns:
        Formatted XML context string to inject into Claude's context
    """
    instructions = routing_result.get("instructions", [])
    count = routing_result.get("count", 0)
    guidance_action = routing_result.get("guidance_action")
    procedural_warning = routing_result.get("procedural_warning")
    friction_risk = routing_result.get("friction_risk_watch")

    # Early exit if nothing to inject
    if count == 0 and not guidance_action and not procedural_warning:
        return ""

    # Start building XML output
    output_parts = []
    output_parts.append('<pongogo_routing context="automatic_discovery">\n')

    # =========================================================================
    # DIRECTIVE: What Claude MUST do (CLR-1: Colleague-test clarity)
    # =========================================================================
    output_parts.append("<directive>\n")
    output_parts.append(
        "You MUST read and follow these instructions before responding to the user.\n"
    )
    output_parts.append(
        "These were automatically discovered based on the user's message context.\n"
    )
    output_parts.append("</directive>\n\n")

    # =========================================================================
    # GUIDANCE ACTION: User preference capture (blocking)
    # =========================================================================
    if guidance_action:
        output_parts.append('<action type="guidance_capture" priority="blocking">\n')
        output_parts.append("<requirement>\n")
        output_parts.append(
            "MANDATORY: Call log_user_guidance() MCP tool BEFORE responding.\n"
        )
        output_parts.append("</requirement>\n")
        output_parts.append(
            f"<directive>{guidance_action.get('directive', '')}</directive>\n"
        )
        output_parts.append("<parameters>\n")
        output_parts.append(
            f"{json.dumps(guidance_action.get('parameters', {}), indent=2)}\n"
        )
        output_parts.append("</parameters>\n")
        output_parts.append("<rationale>\n")
        output_parts.append(
            "User guidance not captured is lost. The user will repeat themselves, causing friction.\n"
        )
        output_parts.append("</rationale>\n")
        output_parts.append("</action>\n\n")

    # =========================================================================
    # PROCEDURAL WARNING: Must-read instructions
    # =========================================================================
    if procedural_warning:
        output_parts.append('<warning type="procedural">\n')
        output_parts.append(
            f"<message>{procedural_warning.get('warning', '')}</message>\n"
        )
        output_parts.append(
            f"<enforcement>{procedural_warning.get('enforcement', 'Read before executing')}</enforcement>\n"
        )
        output_parts.append("</warning>\n\n")

    # =========================================================================
    # FRICTION RISK WATCH: Active monitoring
    # =========================================================================
    if friction_risk and friction_risk.get("enabled"):
        output_parts.append('<monitoring type="friction_risk">\n')
        output_parts.append(
            f"<guidance_type>{friction_risk.get('guidance_type', 'unknown')}</guidance_type>\n"
        )
        output_parts.append(
            f"<echo_detected>{friction_risk.get('echo_detected', False)}</echo_detected>\n"
        )
        output_parts.append(
            f"<frustration_level>{friction_risk.get('frustration_level', 'none')}</frustration_level>\n"
        )
        output_parts.append("</monitoring>\n\n")

    # =========================================================================
    # INSTRUCTIONS: Routed instruction content
    # =========================================================================
    if count > 0:
        output_parts.append(f'<instructions count="{count}">\n')

        for _idx, instruction in enumerate(instructions, 1):
            inst_id = instruction.get("id", "unknown")
            category = instruction.get("category", "unknown")
            description = instruction.get("description", "")
            score = instruction.get("routing_score", 0)
            priority = instruction.get("priority", "P2")
            file_path = instruction.get("file_path", "")
            content = instruction.get("content", "")

            output_parts.append(
                f'<instruction id="{inst_id}" relevance="{score}" priority="{priority}">\n'
            )
            output_parts.append(f"<category>{category}</category>\n")

            if file_path:
                output_parts.append(f"<file>{file_path}</file>\n")

            if description:
                output_parts.append(f"<summary>{description}</summary>\n")

            # Extract and include evaluation criteria if present
            if content:
                criteria = _extract_evaluation_criteria(content)
                if criteria["success"] or criteria["failure"]:
                    output_parts.append("<compliance_criteria>\n")
                    if criteria["success"]:
                        output_parts.append("<success>\n")
                        for signal in criteria["success"]:
                            output_parts.append(f"- {signal}\n")
                        output_parts.append("</success>\n")
                    if criteria["failure"]:
                        output_parts.append("<failure>\n")
                        for signal in criteria["failure"]:
                            output_parts.append(f"- {signal}\n")
                        output_parts.append("</failure>\n")
                    output_parts.append("</compliance_criteria>\n")

                # Include content (frontmatter stripped, truncated)
                content_body = extract_content_without_frontmatter(content)
                excerpt = (
                    content_body[:1500] + "\n[...truncated]"
                    if len(content_body) > 1500
                    else content_body
                )
                output_parts.append("<content>\n")
                output_parts.append(excerpt)
                output_parts.append("\n</content>\n")

            output_parts.append("</instruction>\n\n")

        output_parts.append("</instructions>\n\n")

    # =========================================================================
    # EXPECTED BEHAVIOR: How Claude should process (COT-2, HALL-1)
    # =========================================================================
    output_parts.append("<expected_behavior>\n")
    output_parts.append("After reading the above:\n")
    output_parts.append("1. Identify which instruction applies to the user's request\n")
    output_parts.append("2. READ the instruction content (not from memory)\n")
    output_parts.append("3. Follow step-by-step guidance if present\n")
    output_parts.append("4. Check compliance_criteria to verify correct execution\n")
    output_parts.append(
        "5. If unsure about requirements, ask the user rather than guessing\n"
    )
    output_parts.append("</expected_behavior>\n\n")

    output_parts.append("</pongogo_routing>")

    return "".join(output_parts)
