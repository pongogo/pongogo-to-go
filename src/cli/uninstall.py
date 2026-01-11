"""Pongogo uninstall cleanup utilities.

This module provides the cleanup logic for removing Pongogo configuration
from various config files. It's designed to be called from the shell wrapper
to avoid inline Python in deploy.yml (which hit GitHub's expression limit).
"""

import json
import os
import sys
from pathlib import Path

import typer

from .console import console, print_error, print_success, print_warning

app = typer.Typer(
    name="uninstall-cleanup",
    help="Internal cleanup utilities for uninstall",
    hidden=True,  # Don't show in main help
)


def debug_print(message: str, debug: bool) -> None:
    """Print debug message if debug mode is enabled."""
    if debug:
        console.print(f"[dim][DEBUG] {message}[/dim]")


def remove_from_mcp_json(path: str, debug: bool = False) -> bool:
    """Remove pongogo-knowledge from an MCP config file.

    Args:
        path: Path to the .mcp.json file
        debug: Whether to print debug output

    Returns:
        True if successful, False if error occurred
    """
    abs_path = os.path.abspath(path)
    debug_print(f"Processing: {abs_path}", debug)

    if not os.path.exists(path):
        debug_print(f"File not found: {abs_path}", debug)
        return True  # Not an error - file doesn't exist

    try:
        with open(path, "r") as f:
            config = json.load(f)

        if debug:
            keys = list(config.get("mcpServers", {}).keys())
            debug_print(f"Keys in mcpServers: {keys}", debug)

        if "mcpServers" in config and "pongogo-knowledge" in config["mcpServers"]:
            del config["mcpServers"]["pongogo-knowledge"]

            if not config["mcpServers"]:
                # Remove file if mcpServers is now empty
                os.remove(path)
                # Verify removal
                if os.path.exists(path):
                    print_error(f"Failed to remove {abs_path} - file still exists!")
                    return False
                print_success(f"Removed {path} (no other MCP servers configured)")
            else:
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
                print_success(f"Removed pongogo-knowledge from {path}")
        else:
            print_success(f"No pongogo-knowledge config found in {path}")

        return True

    except PermissionError as e:
        print_error(f"Permission denied: {abs_path} - {e}")
        return False
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {abs_path}: {e}")
        return False
    except Exception as e:
        print_error(f"Could not modify {path}: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        return False


def remove_from_claude_mcp_json(debug: bool = False) -> bool:
    """Remove pongogo-knowledge from .claude/mcp.json.

    Also removes empty .claude directory if applicable.
    """
    path = ".claude/mcp.json"
    abs_path = os.path.abspath(path)
    debug_print(f"Processing: {abs_path}", debug)

    if not os.path.exists(path):
        debug_print(f"File not found: {abs_path}", debug)
        return True

    try:
        with open(path, "r") as f:
            config = json.load(f)

        if "mcpServers" in config and "pongogo-knowledge" in config["mcpServers"]:
            del config["mcpServers"]["pongogo-knowledge"]

            if not config["mcpServers"]:
                os.remove(path)
                if os.path.exists(path):
                    print_error(f"Failed to remove {abs_path} - file still exists!")
                    return False

                # Remove .claude dir if empty
                if os.path.isdir(".claude") and not os.listdir(".claude"):
                    os.rmdir(".claude")
                    print_success("Removed .claude/mcp.json and empty .claude/ directory")
                else:
                    print_success("Removed .claude/mcp.json (no other MCP servers)")
            else:
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
                print_success("Removed pongogo-knowledge from .claude/mcp.json")
        else:
            print_success("No pongogo-knowledge config found in .claude/mcp.json")

        return True

    except PermissionError as e:
        print_error(f"Permission denied: {abs_path} - {e}")
        return False
    except Exception as e:
        print_error(f"Could not modify .claude/mcp.json: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        return False


def remove_hooks_from_settings(debug: bool = False) -> bool:
    """Remove pongogo-route hooks from .claude/settings.local.json."""
    path = ".claude/settings.local.json"
    abs_path = os.path.abspath(path)
    debug_print(f"Processing: {abs_path}", debug)

    if not os.path.exists(path):
        debug_print(f"File not found: {abs_path}", debug)
        return True

    try:
        with open(path, "r") as f:
            config = json.load(f)

        modified = False
        if "hooks" in config and "UserPromptSubmit" in config["hooks"]:
            new_hooks = []
            for hook_group in config["hooks"]["UserPromptSubmit"]:
                if "hooks" in hook_group:
                    hook_group["hooks"] = [
                        h
                        for h in hook_group["hooks"]
                        if "pongogo-route" not in h.get("command", "")
                    ]
                    if hook_group["hooks"]:
                        new_hooks.append(hook_group)
                else:
                    new_hooks.append(hook_group)

            if new_hooks:
                config["hooks"]["UserPromptSubmit"] = new_hooks
            else:
                del config["hooks"]["UserPromptSubmit"]

            if not config["hooks"]:
                del config["hooks"]

            modified = True

        if modified:
            if not config:
                os.remove(path)
                if os.path.exists(path):
                    print_error(f"Failed to remove {abs_path} - file still exists!")
                    return False
                print_success("Removed .claude/settings.local.json (no other settings)")
            else:
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
                print_success("Removed pongogo hooks from .claude/settings.local.json")
        else:
            print_success("No pongogo hooks found in .claude/settings.local.json")

        return True

    except PermissionError as e:
        print_error(f"Permission denied: {abs_path} - {e}")
        return False
    except Exception as e:
        print_error(f"Could not modify .claude/settings.local.json: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        return False


def remove_from_global_claude_json(debug: bool = False) -> bool:
    """Remove pongogo-knowledge from ~/.claude.json (legacy location)."""
    path = os.path.expanduser("~/.claude.json")
    debug_print(f"Processing: {path}", debug)

    if not os.path.exists(path):
        debug_print(f"File not found: {path}", debug)
        return True

    try:
        with open(path, "r") as f:
            config = json.load(f)

        if "mcpServers" in config and "pongogo-knowledge" in config["mcpServers"]:
            del config["mcpServers"]["pongogo-knowledge"]
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            print_success("Removed pongogo-knowledge from ~/.claude.json")
        else:
            print_success("No pongogo-knowledge config found in ~/.claude.json")

        return True

    except PermissionError as e:
        print_error(f"Permission denied: {path} - {e}")
        return False
    except Exception as e:
        print_error(f"Could not modify ~/.claude.json: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        return False


@app.command(name="cleanup")
def cleanup_command(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output"),
) -> None:
    """Remove Pongogo configuration from all config files.

    This command removes pongogo-knowledge entries from:
    - .mcp.json (project root)
    - .claude/mcp.json (Claude Code project config)
    - .claude/settings.local.json (hooks)
    - ~/.claude.json (global/legacy config)
    """
    debug_print(f"CWD: {os.getcwd()}", debug)

    success = True

    # Remove from .mcp.json
    if not remove_from_mcp_json(".mcp.json", debug):
        success = False

    # Remove from .claude/mcp.json
    if not remove_from_claude_mcp_json(debug):
        success = False

    # Remove hooks from settings
    if not remove_hooks_from_settings(debug):
        success = False

    # Remove from global config
    if not remove_from_global_claude_json(debug):
        success = False

    if not success:
        raise typer.Exit(1)


def main() -> None:
    """Entry point for pongogo-cleanup command."""
    app()


if __name__ == "__main__":
    main()
