"""
Routing Result Formatter for Pongogo-to-Go.

Formats routing results for Claude consumption via UserPromptSubmit hook.

CRITICAL: This formatter includes ALL action directives, not just instructions.
Unlike Super Pongogo's claude_code_adapter.py (which drops guidance_action),
this implementation properly exposes:
- guidance_action: Tells Claude to call log_user_guidance()
- procedural_warning: Warns about procedural instructions
- friction_risk_watch: Signals for friction detection

Related: Task #482, Sub-Task #485
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


def format_routing_results(
    routing_result: dict[str, Any],
    message: str = "",
    enable_auto_read: bool = True,
) -> str:
    """
    Format routing results for Claude consumption via hook.

    CRITICAL: This function includes ALL action directives from the router,
    not just instructions. This fixes the bug in Super Pongogo where
    guidance_action was dropped.

    Args:
        routing_result: Results from router.route() call
        message: Original user message (for context)
        enable_auto_read: If True, include auto-read instructions for critical operations

    Returns:
        Formatted context string to inject into Claude's context
    """
    instructions = routing_result.get("instructions", [])
    count = routing_result.get("count", 0)

    # Start building output
    output_parts = []

    # =========================================================================
    # CRITICAL: Include guidance_action directive (Task #482 fix)
    # =========================================================================
    guidance_action = routing_result.get("guidance_action")
    if guidance_action:
        output_parts.append("## ⚠️ MANDATORY: User Guidance Detected\n")
        output_parts.append(
            "**BLOCKING REQUIREMENT**: You MUST call the `log_user_guidance()` MCP tool "
            "BEFORE responding to the user. This captures user preferences for future work.\n\n"
        )
        output_parts.append(f"{guidance_action.get('directive', '')}\n\n")
        output_parts.append("**Call with these parameters**:\n")
        output_parts.append(
            f"```json\n{json.dumps(guidance_action.get('parameters', {}), indent=2)}\n```\n\n"
        )
        output_parts.append(
            "**Why this matters**: User guidance that isn't captured is lost. "
            "The user will have to repeat themselves, causing friction.\n\n"
        )

    # =========================================================================
    # CRITICAL: Include procedural_warning (Task #482 fix)
    # =========================================================================
    procedural_warning = routing_result.get("procedural_warning")
    if procedural_warning:
        output_parts.append("## PROCEDURAL INSTRUCTION WARNING\n")
        output_parts.append(f"{procedural_warning.get('warning', '')}\n\n")
        output_parts.append(
            f"**Enforcement**: {procedural_warning.get('enforcement', 'Read before executing')}\n\n"
        )

    # =========================================================================
    # CRITICAL: Include friction_risk_watch (Task #482 fix)
    # =========================================================================
    friction_risk = routing_result.get("friction_risk_watch")
    if friction_risk and friction_risk.get("enabled"):
        output_parts.append("## Friction Risk Watch Active\n")
        output_parts.append(
            f"- **Guidance Type**: {friction_risk.get('guidance_type', 'unknown')}\n"
        )
        output_parts.append(
            f"- **Echo Detected**: {friction_risk.get('echo_detected', False)}\n"
        )
        output_parts.append(
            f"- **Frustration Level**: {friction_risk.get('frustration_level', 'none')}\n\n"
        )

    # =========================================================================
    # Standard instruction routing (existing logic)
    # =========================================================================
    if count == 0 and not guidance_action and not procedural_warning:
        return ""  # No context to inject

    if count > 0:
        output_parts.append("## Relevant Pongogo Instructions\n")
        output_parts.append(
            f"Found {count} relevant instruction(s) for this context:\n\n"
        )

        for idx, instruction in enumerate(instructions, 1):
            inst_id = instruction.get("id", "unknown")
            category = instruction.get("category", "unknown")
            description = instruction.get("description", "")
            score = instruction.get("routing_score", 0)
            file_path = instruction.get("file_path", "")

            output_parts.append(
                f"### {idx}. {inst_id} (category: {category}, relevance: {score})\n"
            )

            if file_path:
                output_parts.append(f"*File: {file_path}*\n")

            if description:
                output_parts.append(f"{description}\n")

            # Include excerpt of content (first 1000 chars, skip frontmatter)
            content = instruction.get("content", "")
            if content:
                content_body = extract_content_without_frontmatter(content)
                excerpt = (
                    content_body[:1000] + "..."
                    if len(content_body) > 1000
                    else content_body
                )
                output_parts.append(f"```\n{excerpt}\n```\n\n")

    # Footer
    if output_parts:
        output_parts.append("---\n")
        output_parts.append(
            "*Note: These instructions were automatically discovered based on your message context.*\n"
        )

    return "".join(output_parts)
