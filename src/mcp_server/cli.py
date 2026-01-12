#!/usr/bin/env python3
"""
CLI entry points for Pongogo-to-Go.

Provides command-line interface for hook-based routing.
The pongogo-route command is called by the UserPromptSubmit hook
to route user messages and return formatted context.

Related: Task #482, Sub-Task #483
"""

import json
import sys
from pathlib import Path

import mcp_server.engines  # noqa: F401 - imported for side effect (engine registration)
import mcp_server.pongogo_router  # noqa: F401 - imported for side effect (set_default_engine)
from mcp_server.config import (
    get_core_instructions_path,
    get_knowledge_path,
    get_routing_config,
    load_config,
)
from mcp_server.formatter import format_routing_results
from mcp_server.instruction_handler import InstructionHandler
from mcp_server.routing_engine import create_router


def route_cli() -> None:
    """
    CLI entry point for hook-based routing.

    Reads user message from stdin JSON (UserPromptSubmit hook format)
    or from command line args, routes it through the knowledge base,
    and prints formatted results to stdout.

    UserPromptSubmit hook sends JSON:
        {"prompt": "user message", "session_id": "...", "cwd": "..."}

    Usage:
        # Via UserPromptSubmit hook (JSON on stdin)
        echo '{"prompt": "message"}' | pongogo-route

        # Direct CLI usage (args)
        pongogo-route "user message here"

    Exit codes:
        0: Success (output printed to stdout)
        1: Error during routing
    """
    # Read message from args (direct CLI) or stdin JSON (hook)
    if len(sys.argv) > 1:
        # Direct CLI usage: pongogo-route "message"
        message = " ".join(sys.argv[1:])
    else:
        # Hook usage: JSON on stdin from UserPromptSubmit
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            sys.exit(0)

        try:
            # Parse JSON from hook
            input_data = json.loads(stdin_data)
            message = input_data.get("prompt", "")
        except json.JSONDecodeError:
            # Fallback: treat stdin as plain text (backward compatibility)
            message = stdin_data

    if not message:
        # No message, no output - exit cleanly
        sys.exit(0)

    try:
        # Load configuration
        server_dir = Path(__file__).parent
        server_config = load_config(server_dir=server_dir)

        # Initialize instruction handler
        knowledge_path = get_knowledge_path(server_config, server_dir)
        core_path = get_core_instructions_path()
        handler = InstructionHandler(knowledge_path, core_path=core_path)
        handler.load_instructions()

        # Create router with config
        routing_config = get_routing_config(server_config)
        router = create_router(handler, routing_config)

        # Route the message
        result = router.route(message, limit=5)

        # Format and output
        formatted = format_routing_results(result, message=message)
        if formatted:
            print(formatted)

    except Exception as e:
        # Log error to stderr, don't pollute stdout
        print(f"Pongogo routing error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    route_cli()
