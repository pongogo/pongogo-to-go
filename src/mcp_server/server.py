#!/usr/bin/env python3
"""
Pongogo Knowledge MCP Server

FastMCP server providing access to Pongogo instruction files via Model Context Protocol.
Implements intelligent routing using NLP, taxonomy, and context-based matching.

Features:
- Intelligent routing (NLP, taxonomy, context matching)
- Automatic reindexing via file watcher
- Manual reindexing via /pongogo-reindex command
- Health check (5-minute consistency verification)

Phase 1 Scope: 54+ instruction files across 14+ categories
Future: Wiki pages, tactical guides, pattern library
"""

import logging
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Import engines package to auto-register frozen engine versions
import mcp_server.engines  # noqa: F401 - imported for side effect (engine registration)
from mcp_server.config import (
    get_core_instructions_path,
    get_knowledge_path,
    get_routing_config,
    load_config,
)

# Discovery system for observation-triggered promotion
from mcp_server.discovery_system import DiscoverySystem
from mcp_server.instruction_handler import InstructionHandler
from mcp_server.routing_engine import (
    RoutingEngine,
    create_router,
    get_available_engines,
    get_engine_features,
)
from mcp_server.upgrade import detect_install_method, get_current_version

# Upgrade functionality
from mcp_server.upgrade import upgrade as do_upgrade

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("pongogo-knowledge")

# Load configuration
# Priority: PONGOGO_CONFIG_PATH env var > ./pongogo-config.yaml > defaults
SERVER_DIR = Path(__file__).parent
server_config = load_config(server_dir=SERVER_DIR)

# Initialize handlers (global state)
# Knowledge path from config or default (../knowledge/instructions)
KNOWLEDGE_BASE_PATH = get_knowledge_path(server_config, SERVER_DIR)
# Core instructions path (bundled in package, protected from deletion)
CORE_INSTRUCTIONS_PATH = get_core_instructions_path()
instruction_handler = InstructionHandler(
    KNOWLEDGE_BASE_PATH, core_path=CORE_INSTRUCTIONS_PATH
)

# Create router with config
# Config specifies engine version and feature flags
routing_config = get_routing_config(server_config)
router: RoutingEngine = create_router(instruction_handler, routing_config)
# Note: Routing engine version now comes from router.version
# Version format: durian-{major}.{minor}[-dev] (e.g., durian-0.5)

# Initialize discovery system for observation-triggered promotion
# Project root is parent of .pongogo directory (which is parent of instructions/)
PROJECT_ROOT = KNOWLEDGE_BASE_PATH.parent.parent
discovery_system: DiscoverySystem | None = None
try:
    if (PROJECT_ROOT / ".pongogo" / "discovery.db").exists():
        discovery_system = DiscoverySystem(PROJECT_ROOT)
        logger.info(f"Discovery system initialized for: {PROJECT_ROOT}")
except Exception as e:
    logger.warning(f"Discovery system not available: {e}")

# Reindex state management
_reindex_lock = threading.Lock()
_last_reindex_time = time.time()
_debounce_timer: threading.Timer | None = None
_last_manual_reindex = 0.0  # Timestamp of last manual reindex
MIN_MANUAL_REINDEX_INTERVAL = 10.0  # Minimum 10 seconds between manual reindexes

# Shutdown management (graceful shutdown on SIGTERM/SIGINT)
_shutdown_event = threading.Event()
_observer: Observer | None = None


class InstructionFileEventHandler(FileSystemEventHandler):
    """
    File watcher event handler for instruction files.

    Implements debouncing to handle batch file changes efficiently.
    Only reacts to actual file modifications (created, modified, deleted, moved),
    not file reads (opened, closed) to prevent reindex storms.
    """

    def __init__(self, debounce_seconds: float = 3.0):
        """
        Initialize event handler with debouncing.

        Args:
            debounce_seconds: Seconds to wait after last file event before reindexing
        """
        super().__init__()
        self.debounce_seconds = debounce_seconds
        self._pending_events: set[str] = set()

    def _should_process(self, event: FileSystemEvent) -> bool:
        """
        Determine if event should trigger reindex.

        Args:
            event: File system event

        Returns:
            True if event represents actual file change (not just read)
        """
        # Ignore directory events
        if event.is_directory:
            return False

        # Only process .instructions.md files
        src_path = Path(event.src_path)
        return src_path.name.endswith(".instructions.md")

    def _handle_event(self, event: FileSystemEvent):
        """
        Process file system event and trigger debounced reindex.

        Args:
            event: File system event (created, modified, deleted, moved)
        """
        if not self._should_process(event):
            return

        src_path = Path(event.src_path)
        event_type = event.event_type
        logger.info(f"File {event_type}: {src_path.name}")

        # Add to pending events set
        self._pending_events.add(event.src_path)

        # Cancel existing timer if any
        global _debounce_timer
        if _debounce_timer is not None:
            _debounce_timer.cancel()

        # Start new debounce timer
        _debounce_timer = threading.Timer(self.debounce_seconds, self._trigger_reindex)
        _debounce_timer.start()

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events (content changed)."""
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events (new file)."""
        self._handle_event(event)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events (file removed)."""
        self._handle_event(event)

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events."""
        self._handle_event(event)

    def _trigger_reindex(self):
        """
        Trigger reindex after debounce period.

        Called by debounce timer after no file events for debounce_seconds.
        """
        if not self._pending_events:
            return

        event_count = len(self._pending_events)
        logger.info(
            f"Debounce period complete - triggering reindex ({event_count} file(s) changed)"
        )

        # Clear pending events
        self._pending_events.clear()

        # Trigger reindex
        _reindex_knowledge_base()


def _reindex_knowledge_base():
    """
    Reindex instruction files (atomic swap of metadata).

    Thread-safe reindexing with lock to prevent concurrent reloads.
    Uses atomic swap pattern: create new handler, validate, swap.
    """
    global instruction_handler, router, _last_reindex_time

    with _reindex_lock:
        try:
            start_time = time.time()
            logger.info("=== Starting knowledge base reindex ===")

            # Create new handler instance (loads fresh from disk)
            # Core path is constant (bundled), user path reloads from disk
            new_handler = InstructionHandler(
                KNOWLEDGE_BASE_PATH, core_path=CORE_INSTRUCTIONS_PATH
            )
            new_count = new_handler.load_instructions()

            # Create new router with new handler (factory pattern - )
            # Preserve current config
            new_router = create_router(new_handler, routing_config)

            # Atomic swap (zero-downtime)
            old_count = len(instruction_handler.instructions)
            instruction_handler = new_handler
            router = new_router
            _last_reindex_time = time.time()

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"=== Reindex complete: {old_count} → {new_count} instructions "
                f"(engine: {new_router.version}, {elapsed_ms:.1f}ms) ==="
            )

            return {
                "success": True,
                "old_count": old_count,
                "new_count": new_count,
                "elapsed_ms": elapsed_ms,
                "engine": new_router.version,  # Include engine version
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Reindex failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Server lifecycle hooks
@mcp.tool()
async def get_instructions(
    topic: str | None = None, category: str | None = None, exact_match: bool = False
) -> dict:
    """
    Get relevant instruction files by topic or category.

    Args:
        topic: Topic or keyword to search (e.g., "epic", "github", "testing")
        category: Category to filter by (e.g., "project_management", "github_integration")
        exact_match: If True, match exact filename; if False, search across content

    Returns:
        Dictionary with:
        - instructions: List of matching instruction files
        - count: Number of results
        - query: Search parameters used

    Examples:
        # Get all instructions in github_integration category
        get_instructions(category="github_integration")

        # Search for epic-related instructions across all categories
        get_instructions(topic="epic")

        # Get specific instruction file
        get_instructions(category="project_management", topic="epic_management", exact_match=True)
    """
    try:
        logger.info(
            f"get_instructions called: topic={topic}, category={category}, exact_match={exact_match}"
        )

        if exact_match and topic and category:
            # Exact match: get specific file
            instruction = instruction_handler.get_instruction(category, topic)
            if instruction:
                return {
                    "instructions": [instruction],
                    "count": 1,
                    "query": {
                        "topic": topic,
                        "category": category,
                        "exact_match": True,
                    },
                }
            else:
                return {
                    "instructions": [],
                    "count": 0,
                    "query": {
                        "topic": topic,
                        "category": category,
                        "exact_match": True,
                    },
                    "error": f"Instruction not found: {category}/{topic}",
                }

        elif category:
            # Filter by category
            instructions = instruction_handler.get_instructions_by_category(category)
            if topic:
                # Further filter by topic within category
                instructions = [
                    i
                    for i in instructions
                    if topic.lower() in i["id"].lower()
                    or topic.lower() in i["content"].lower()
                ]

            return {
                "instructions": instructions,
                "count": len(instructions),
                "query": {"topic": topic, "category": category, "exact_match": False},
            }

        elif topic:
            # Search across all categories
            instructions = instruction_handler.search_instructions(topic)
            return {
                "instructions": instructions,
                "count": len(instructions),
                "query": {"topic": topic, "exact_match": False},
            }

        else:
            # Get all instructions
            instructions = instruction_handler.get_all_instructions()
            return {
                "instructions": instructions,
                "count": len(instructions),
                "query": {"all": True},
            }

    except Exception as e:
        logger.error(f"Error in get_instructions: {e}", exc_info=True)
        return {
            "instructions": [],
            "count": 0,
            "query": {"topic": topic, "category": category, "exact_match": exact_match},
            "error": str(e),
        }


@mcp.tool()
async def search_instructions(query: str, limit: int = 10) -> dict:
    """
    Full-text search across all instruction files.

    Args:
        query: Search query string
        limit: Maximum number of results to return (default: 10)

    Returns:
        Dictionary with:
        - results: List of search results with snippets
        - count: Number of results
        - query: Search query used

    Examples:
        # Search for MCP-related instructions
        search_instructions("mcp server")

        # Search for GitHub API instructions
        search_instructions("github api", limit=5)
    """
    try:
        logger.info(f"search_instructions called: query={query}, limit={limit}")

        results = instruction_handler.search_instructions(query, limit=limit)

        return {"results": results, "count": len(results), "query": query}

    except Exception as e:
        logger.error(f"Error in search_instructions: {e}", exc_info=True)
        return {"results": [], "count": 0, "query": query, "error": str(e)}


@mcp.tool()
async def route_instructions(
    message: str, context: dict | None = None, limit: int = 5
) -> dict:
    """
    Intelligently route to relevant instruction files using NLP + taxonomy + context.

    This is Pongogo's differentiator - semantic routing beyond simple path/glob matching.

    Args:
        message: User message or query
        context: Optional context dictionary with:
            - files: List of file paths in current context
            - directories: List of directory paths
            - branch: Current git branch
            - language: Programming language
        limit: Maximum number of instructions to return (default: 5)

    Returns:
        Dictionary with:
        - instructions: List of routed instructions with confidence scores
        - count: Number of results
        - routing_analysis: Breakdown of how routing decision was made
        - routing_engine_version: Version of routing engine that produced results
        - procedural_warning: Warning when procedural instructions routed
          Contains warning message, list of procedural instructions, and enforcement guidance

    Examples:
        # Route based on message only
        route_instructions("How do I create a new Epic?")

        # Route with file context
        route_instructions(
            "Fix this API integration",
            context={"files": ["src/github/api.py"], "language": "python"}
        )
    """
    try:
        logger.info(
            f"route_instructions called: message={message}, context={context}, limit={limit}"
        )

        results = router.route(message, context=context, limit=limit)

        # Add routing engine version to response
        # Use router.version from RoutingEngine interface instead of hardcoded constant
        results["routing_engine_version"] = router.version

        # Observation-triggered discovery promotion
        # Check discoveries for matches and auto-promote on first observation
        if discovery_system:
            try:
                promoted_discoveries = _check_and_promote_discoveries(message, results)
                if promoted_discoveries:
                    results["promoted_discoveries"] = promoted_discoveries
                    logger.info(
                        f"Auto-promoted {len(promoted_discoveries)} discoveries"
                    )
            except Exception as e:
                logger.warning(f"Discovery promotion check failed: {e}")

        return results

    except Exception as e:
        logger.error(f"Error in route_instructions: {e}", exc_info=True)
        return {
            "instructions": [],
            "count": 0,
            "routing_analysis": {},
            "routing_engine_version": router.version if router else "unknown",
            "error": str(e),
        }


def _check_and_promote_discoveries(message: str, routing_results: dict) -> list:
    """
    Check discovery database for matches and auto-promote on first observation.

    Args:
        message: User message/query
        routing_results: Results from router.route() for keyword extraction

    Returns:
        List of promoted discovery info dicts
    """
    if not discovery_system:
        return []

    promoted = []

    # Extract keywords from routing analysis if available
    keywords = []
    routing_analysis = routing_results.get("routing_analysis", {})
    if "query_keywords" in routing_analysis:
        keywords = routing_analysis["query_keywords"]
    elif "keywords" in routing_analysis:
        keywords = routing_analysis["keywords"]
    else:
        # Fallback: extract simple keywords from message
        import re

        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", message.lower())
        keywords = list(set(words))[:20]

    if not keywords:
        return []

    # Find matching discoveries
    matches = discovery_system.find_matches(keywords, limit=3)

    for discovery in matches:
        if discovery.status == "DISCOVERED":
            # Auto-promote: create instruction file
            instruction_path = discovery_system.promote(discovery.id)
            if instruction_path:
                promoted.append(
                    {
                        "discovery_id": discovery.id,
                        "source_file": discovery.source_file,
                        "section_title": discovery.section_title,
                        "instruction_file": instruction_path,
                        "message": f"Auto-created instruction from {discovery.source_type} discovery",
                    }
                )

                # Trigger reindex to include new instruction file
                # (async reindex will pick it up on next file watcher event)
                logger.info(f"Discovery #{discovery.id} promoted to {instruction_path}")

    return promoted


@mcp.resource("instruction://pongogo/{category}/{name}")
async def get_instruction_resource(category: str, name: str) -> str:
    """
    MCP resource handler for instruction:// URI pattern.

    Args:
        category: Instruction category (e.g., "project_management")
        name: Instruction name (e.g., "epic_management")

    Returns:
        Full instruction file content as string
    """
    try:
        logger.info(f"Resource requested: instruction://pongogo/{category}/{name}")

        instruction = instruction_handler.get_instruction(category, name)
        if instruction:
            return instruction["content"]
        else:
            raise ValueError(f"Instruction not found: {category}/{name}")

    except Exception as e:
        logger.error(f"Error getting resource: {e}", exc_info=True)
        raise


@mcp.tool()
async def reindex_knowledge_base(force: bool = False) -> dict:
    """
    Manually trigger knowledge base reindex.

    Reloads all instruction files from disk, useful after bulk updates or
    for testing. Includes spam prevention (10-second minimum interval).

    Args:
        force: If True, bypass spam prevention interval check

    Returns:
        Dictionary with reindex results:
        - success: True if reindex succeeded
        - old_count: Number of instructions before reindex
        - new_count: Number of instructions after reindex
        - elapsed_ms: Reindex duration in milliseconds
        - skipped: True if skipped due to spam prevention

    Examples:
        # Normal reindex
        reindex_knowledge_base()

        # Force reindex (bypass spam prevention)
        reindex_knowledge_base(force=True)
    """
    global _last_manual_reindex

    try:
        logger.info(f"Manual reindex requested (force={force})")

        # Spam prevention: minimum 10 seconds between manual reindexes
        if not force:
            time_since_last = time.time() - _last_manual_reindex
            if time_since_last < MIN_MANUAL_REINDEX_INTERVAL:
                wait_time = MIN_MANUAL_REINDEX_INTERVAL - time_since_last
                logger.warning(
                    f"Manual reindex skipped (spam prevention): "
                    f"wait {wait_time:.1f}s before next manual reindex"
                )
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "spam_prevention",
                    "wait_seconds": round(wait_time, 1),
                    "hint": f"Wait {wait_time:.1f}s or use force=true to bypass",
                }

        # Execute reindex
        result = _reindex_knowledge_base()

        # Update last manual reindex timestamp only if successful
        if result.get("success"):
            _last_manual_reindex = time.time()

        return result

    except Exception as e:
        logger.error(f"Error in manual reindex: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@mcp.tool()
async def switch_engine(engine_version: str | None = None) -> dict:
    """
    Switch routing engine version or list available engines.

    Runtime engine switching for A/B testing and development.

    Args:
        engine_version: Engine version to switch to (e.g., "durian-0.5-dev").
                       If not provided, returns list of available engines.

    Returns:
        Dictionary with:
        - success: True if switch succeeded
        - engine: New engine version (if switched)
        - previous: Previous engine version (if switched)
        - available: List of available engines (if listing)
        - features: Available features for the engine

    Examples:
        # List available engines
        switch_engine()

        # Switch to specific engine
        switch_engine("durian-0.5-dev")
    """
    global router, routing_config

    try:
        # If no version specified, list available engines
        if engine_version is None:
            engines = get_available_engines()
            current = router.version
            engine_info = []

            for eng in engines:
                features = get_engine_features(eng)
                engine_info.append(
                    {
                        "version": eng,
                        "current": eng == current,
                        "features": [f.to_dict() for f in features],
                    }
                )

            return {
                "success": True,
                "action": "list",
                "current_engine": current,
                "available_engines": engine_info,
                "hint": "Use switch_engine('version') to switch engines",
            }

        # Validate engine version exists
        available = get_available_engines()
        if engine_version not in available:
            return {
                "success": False,
                "error": f"Unknown engine: '{engine_version}'",
                "available_engines": available,
                "hint": f"Available engines: {', '.join(available)}",
            }

        # Check if already using requested engine
        previous = router.version
        if engine_version == previous:
            return {
                "success": True,
                "action": "no_change",
                "engine": engine_version,
                "message": f"Already using engine: {engine_version}",
            }

        # Switch engine (atomic swap)
        logger.info(f"Switching routing engine: {previous} → {engine_version}")

        # Update config for new engine
        new_routing_config = {
            "routing": {
                "engine": engine_version,
                "features": routing_config.get("routing", {}).get("features", {}),
            }
        }

        # Create new router with new engine
        new_router = create_router(instruction_handler, new_routing_config)

        # Atomic swap
        router = new_router
        routing_config = new_routing_config

        logger.info(f"Engine switch complete: {previous} → {engine_version}")

        return {
            "success": True,
            "action": "switched",
            "engine": engine_version,
            "previous": previous,
            "description": new_router.description,
            "features": [f.to_dict() for f in get_engine_features(engine_version)],
        }

    except Exception as e:
        logger.error(f"Error switching engine: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "current_engine": router.version if router else "unknown",
        }


@mcp.tool()
async def upgrade_pongogo() -> dict:
    """
    Upgrade Pongogo to the latest version.

    Automatically detects installation method (Docker or pip) and executes
    the appropriate upgrade command. The upgrade takes effect after restarting
    Claude Code.

    Returns:
        Dictionary with:
        - success: True if upgrade succeeded
        - method: Installation method (docker/pip)
        - message: Human-readable status message
        - previous_version: Version before upgrade (if known)
        - new_version: Version after upgrade (for pip only)

    Example:
        # Upgrade Pongogo
        upgrade_pongogo()  # Returns {"success": True, "method": "docker", ...}
    """
    try:
        result = do_upgrade()

        return {
            "success": result.success,
            "method": result.method.value,
            "message": result.message,
            "previous_version": result.previous_version,
            "new_version": result.new_version,
        }

    except Exception as e:
        logger.error(f"Upgrade error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "method": detect_install_method().value,
            "current_version": get_current_version(),
        }


def _check_consistency():
    """
    Periodic health check comparing disk file count vs cached instruction count.

    Runs every 5 minutes in background thread. Auto-triggers reindex if mismatch detected.
    Respects shutdown event for graceful termination.
    """
    while not _shutdown_event.is_set():
        try:
            # Sleep with shutdown awareness (check every second)
            for _ in range(300):  # 5 minutes = 300 seconds
                if _shutdown_event.is_set():
                    logger.info("Health check thread shutting down...")
                    return
                time.sleep(1)

            # Count instruction files on disk
            disk_count = sum(1 for _ in KNOWLEDGE_BASE_PATH.rglob("*.instructions.md"))

            # Count cached instructions
            cache_count = len(instruction_handler.instructions)

            if disk_count != cache_count:
                logger.warning(
                    f"Consistency check failed: disk={disk_count}, cache={cache_count} "
                    f"(triggering auto-reindex)"
                )
                _reindex_knowledge_base()
            else:
                logger.debug(
                    f"Consistency check passed: {disk_count} instruction files"
                )

        except Exception as e:
            logger.error(f"Consistency check error: {e}", exc_info=True)


def _start_file_watcher():
    """
    Start file watcher for automatic reindexing.

    Watches knowledge/instructions/**/*.instructions.md files.
    Runs in background thread with 3-second debouncing.
    Respects shutdown event for graceful termination.
    """
    global _observer

    try:
        event_handler = InstructionFileEventHandler(debounce_seconds=3.0)
        _observer = Observer()
        _observer.schedule(event_handler, str(KNOWLEDGE_BASE_PATH), recursive=True)
        _observer.start()
        logger.info(f"File watcher started: {KNOWLEDGE_BASE_PATH}")

        # Keep observer running until shutdown
        while not _shutdown_event.is_set():
            time.sleep(1)

        # Graceful shutdown
        logger.info("File watcher shutting down...")
        _observer.stop()
        _observer.join(timeout=5)
        logger.info("File watcher stopped")

    except Exception as e:
        logger.error(f"File watcher error: {e}", exc_info=True)


def _signal_handler(sig, frame):
    """
    Graceful shutdown handler for SIGTERM/SIGINT signals.

    Coordinates shutdown of file watcher, health check, and MCP server.
    """
    logger.info(
        f"Received signal {sig} ({signal.Signals(sig).name}), initiating graceful shutdown..."
    )

    # Set shutdown event (background threads will terminate)
    _shutdown_event.set()

    # Cancel any pending debounce timer
    global _debounce_timer
    if _debounce_timer is not None:
        _debounce_timer.cancel()
        logger.info("Cancelled pending debounce timer")

    logger.info("Shutdown complete")
    sys.exit(0)


def main():
    """Main entry point for pongogo-server CLI command.

    Starts the Pongogo Knowledge MCP Server with:
    - Instruction file loading and validation
    - File watcher for auto-reindex
    - Health check thread
    - Signal handlers for graceful shutdown
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info("=== Starting Pongogo Knowledge MCP Server ===")
    logger.info(f"Knowledge base path: {KNOWLEDGE_BASE_PATH}")

    # Load instruction files (initial load)
    instruction_count = instruction_handler.load_instructions()
    logger.info(f"Loaded {instruction_count} instruction files")
    logger.info(f"Routing engine: {router.version} ({router.description})")

    # CRITICAL: Startup assertion - fail if no instructions loaded
    # This prevents silent failures like the 9-day routing outage (Dec 1-10, 2025)
    # where container path mismatch caused instruction_count=0 without alerting
    if instruction_count == 0:
        logger.critical(
            "FATAL: No instruction files loaded! "
            "Check PONGOGO_KNOWLEDGE_PATH environment variable and volume mounts. "
            f"Expected path: {KNOWLEDGE_BASE_PATH}"
        )
        sys.exit(1)

    # STARTUP TEST: Verify routing actually works end-to-end
    # Tests the full path: instruction loading → router → results
    # NOTE: This test is safe - router.route() only READS from DB, doesn't write.
    # Database writes happen only in the hook (claude_code_adapter.py), not server.
    test_query = "how do I create an epic"
    test_result = router.route(test_query, limit=3)
    test_count = test_result.get("count", 0)
    if test_count == 0:
        logger.critical(
            f"FATAL: Startup routing test failed! "
            f"Query '{test_query}' returned 0 results despite {instruction_count} instructions loaded. "
            f"Router may be misconfigured. Check routing_engine.py and instruction metadata."
        )
        sys.exit(1)
    else:
        logger.info(
            f"Startup routing test passed: '{test_query}' → {test_count} results"
        )

    # Start file watcher in background thread
    watcher_thread = threading.Thread(
        target=_start_file_watcher, daemon=True, name="FileWatcher"
    )
    watcher_thread.start()
    logger.info("File watcher thread started (auto-reindex enabled)")

    # Start consistency check in background thread
    health_check_thread = threading.Thread(
        target=_check_consistency, daemon=True, name="HealthCheck"
    )
    health_check_thread.start()
    logger.info("Health check thread started (5-minute interval)")

    # Start MCP server (blocks until shutdown)
    logger.info("MCP server ready - listening for tool calls")
    logger.info("Signal handlers registered (SIGTERM, SIGINT) for graceful shutdown")
    mcp.run()


if __name__ == "__main__":
    main()
