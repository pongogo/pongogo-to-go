"""
Health check module for Pongogo MCP server.

Provides comprehensive health status checks for diagnostics and monitoring.

Task #470: Implement MCP health check tools
Parent Epic: #463 (enable_routing_event_capture)
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from mcp_server.config import get_project_root
from mcp_server.event_capture import get_events_db_path

logger = logging.getLogger(__name__)


def check_container_status() -> dict[str, Any]:
    """
    Check Docker container status.

    Returns:
        Dictionary with:
        - status: "healthy" | "unhealthy" | "unknown"
        - reason: Optional explanation when not healthy
        - container_id: Optional container ID when available
    """
    try:
        # Note: MCP server runs INSIDE the container, so we check if we're containerized
        # by looking for container markers
        if Path("/.dockerenv").exists():
            return {
                "status": "healthy",
                "reason": "Running inside container",
                "containerized": True,
            }

        # Check cgroup for container indicators
        cgroup_path = Path("/proc/1/cgroup")
        if cgroup_path.exists():
            try:
                cgroup_content = cgroup_path.read_text()
                if "docker" in cgroup_content or "containerd" in cgroup_content:
                    return {
                        "status": "healthy",
                        "reason": "Running inside container (cgroup)",
                        "containerized": True,
                    }
            except Exception:
                pass

        # Not in container - this is fine for development
        return {
            "status": "healthy",
            "reason": "Running on host (development mode)",
            "containerized": False,
        }

    except Exception as e:
        logger.error(f"Error checking container status: {e}")
        return {
            "status": "unknown",
            "reason": str(e),
            "containerized": None,
        }


def check_database_health() -> dict[str, Any]:
    """
    Check events database health.

    Returns:
        Dictionary with:
        - status: "healthy" | "missing" | "locked" | "error"
        - path: Database file path
        - reason: Optional explanation
        - writable: Boolean if database is writable
    """
    db_path = get_events_db_path()

    if not db_path.exists():
        return {
            "status": "missing",
            "path": str(db_path),
            "reason": "Database file not found",
            "writable": False,
        }

    try:
        # Test read + write capability with short timeout
        conn = sqlite3.connect(db_path, timeout=1)
        conn.execute("SELECT 1")
        conn.execute("BEGIN IMMEDIATE")  # Test write lock
        conn.rollback()
        conn.close()

        return {
            "status": "healthy",
            "path": str(db_path),
            "reason": "Database accessible and writable",
            "writable": True,
        }

    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return {
                "status": "locked",
                "path": str(db_path),
                "reason": "Database is locked by another process",
                "writable": False,
            }
        return {
            "status": "error",
            "path": str(db_path),
            "reason": str(e),
            "writable": False,
        }

    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        return {
            "status": "error",
            "path": str(db_path),
            "reason": str(e),
            "writable": False,
        }


def check_event_capture() -> dict[str, Any]:
    """
    Check event capture status (recent activity).

    Returns:
        Dictionary with:
        - status: "active" | "empty" | "stale" | "unknown"
        - total_count: Number of events
        - last_event: Last event timestamp
        - last_event_ago: Human-readable time since last event
        - reason: Explanation
    """
    db_path = get_events_db_path()

    if not db_path.exists():
        return {
            "status": "unknown",
            "total_count": 0,
            "last_event": None,
            "last_event_ago": None,
            "reason": "Database not found",
        }

    try:
        conn = sqlite3.connect(db_path, timeout=1)

        # Get total count
        cursor = conn.execute("SELECT COUNT(*) FROM routing_events")
        total_count = cursor.fetchone()[0]

        if total_count == 0:
            conn.close()
            return {
                "status": "empty",
                "total_count": 0,
                "last_event": None,
                "last_event_ago": None,
                "reason": "No events captured yet",
            }

        # Get last event timestamp
        cursor = conn.execute(
            "SELECT timestamp FROM routing_events ORDER BY timestamp DESC LIMIT 1"
        )
        last_event = cursor.fetchone()[0]
        conn.close()

        # Calculate time since last event
        now = datetime.now(timezone.utc)
        # Handle both offset-naive (no TZ) and offset-aware timestamps
        last_event_str = last_event.replace("Z", "+00:00")
        last_event_dt = datetime.fromisoformat(last_event_str)
        # If timestamp has no timezone info, assume UTC
        if last_event_dt.tzinfo is None:
            last_event_dt = last_event_dt.replace(tzinfo=timezone.utc)
        delta = now - last_event_dt

        # Human-readable time ago
        if delta.days > 0:
            ago = f"{delta.days}d ago"
            status = "stale" if delta.days > 7 else "active"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            ago = f"{hours}h ago"
            status = "stale" if hours > 24 else "active"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            ago = f"{minutes}m ago"
            status = "active"
        else:
            ago = f"{delta.seconds}s ago"
            status = "active"

        return {
            "status": status,
            "total_count": total_count,
            "last_event": last_event,
            "last_event_ago": ago,
            "reason": f"Last event {ago}",
        }

    except Exception as e:
        logger.error(f"Error checking event capture: {e}")
        return {
            "status": "unknown",
            "total_count": 0,
            "last_event": None,
            "last_event_ago": None,
            "reason": str(e),
        }


def check_config_validity() -> dict[str, Any]:
    """
    Check configuration file validity.

    Returns:
        Dictionary with:
        - status: "valid" | "invalid" | "missing"
        - path: Config file path
        - reason: Explanation
        - categories_count: Number of instruction categories (if valid)
    """
    # Check .pongogo directory using project root (not cwd!)
    # This is critical for containers where cwd=/app but config is at /project/.pongogo
    project_root = get_project_root()
    pongogo_dir = project_root / ".pongogo"
    config_path = pongogo_dir / "config.yaml"

    if not pongogo_dir.exists():
        return {
            "status": "missing",
            "path": str(config_path),
            "reason": ".pongogo directory not found",
            "categories_count": 0,
        }

    if not config_path.exists():
        return {
            "status": "missing",
            "path": str(config_path),
            "reason": "config.yaml not found",
            "categories_count": 0,
        }

    try:
        with open(config_path) as f:
            yaml.safe_load(f)

        # Count instruction categories
        instructions_dir = pongogo_dir / "instructions"
        categories_count = 0
        if instructions_dir.exists():
            categories_count = sum(1 for p in instructions_dir.iterdir() if p.is_dir())

        return {
            "status": "valid",
            "path": str(config_path),
            "reason": "Configuration is valid YAML",
            "categories_count": categories_count,
        }

    except yaml.YAMLError as e:
        return {
            "status": "invalid",
            "path": str(config_path),
            "reason": f"Invalid YAML: {e}",
            "categories_count": 0,
        }

    except Exception as e:
        logger.error(f"Error checking config validity: {e}")
        return {
            "status": "invalid",
            "path": str(config_path),
            "reason": str(e),
            "categories_count": 0,
        }


def check_pi_system_storage() -> dict[str, Any]:
    """
    Check PI System storage access (potential_improvements.db).

    This validates that user guidance capture will work correctly.
    Critical for containers where /app/ is read-only but /project/ is writable.

    Returns:
        Dictionary with:
        - status: "healthy" | "error" | "read_only"
        - path: Expected database path
        - reason: Explanation
        - writable: Boolean if storage is writable
    """
    project_root = get_project_root()
    pi_db_path = project_root / ".pongogo" / "potential_improvements.db"
    pongogo_dir = project_root / ".pongogo"

    # Check if .pongogo directory exists
    if not pongogo_dir.exists():
        # Try to create it (will fail if read-only)
        try:
            pongogo_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            return {
                "status": "error",
                "path": str(pi_db_path),
                "reason": f"Cannot create .pongogo directory: {e}",
                "writable": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "path": str(pi_db_path),
                "reason": str(e),
                "writable": False,
            }

    # Test write capability with a temporary file
    test_file = pongogo_dir / ".write_test"
    try:
        test_file.write_text("write_test")
        test_file.unlink()  # Clean up

        # If database exists, also check it's writable
        if pi_db_path.exists():
            try:
                conn = sqlite3.connect(pi_db_path, timeout=1)
                conn.execute("SELECT 1")
                conn.execute("BEGIN IMMEDIATE")
                conn.rollback()
                conn.close()
                return {
                    "status": "healthy",
                    "path": str(pi_db_path),
                    "reason": "PI database exists and is writable",
                    "writable": True,
                }
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    return {
                        "status": "error",
                        "path": str(pi_db_path),
                        "reason": "PI database is locked",
                        "writable": False,
                    }
                return {
                    "status": "error",
                    "path": str(pi_db_path),
                    "reason": f"PI database error: {e}",
                    "writable": False,
                }

        return {
            "status": "healthy",
            "path": str(pi_db_path),
            "reason": "Storage writable, database will be created on first use",
            "writable": True,
        }

    except PermissionError:
        return {
            "status": "read_only",
            "path": str(pi_db_path),
            "reason": "Storage directory is read-only (container issue?)",
            "writable": False,
        }
    except Exception as e:
        logger.error(f"Error checking PI system storage: {e}")
        return {
            "status": "error",
            "path": str(pi_db_path),
            "reason": str(e),
            "writable": False,
        }


def get_health_status() -> dict[str, Any]:
    """
    Get comprehensive health status of Pongogo installation.

    Returns:
        Dictionary with:
        - overall: "healthy" | "degraded" | "unhealthy"
        - container: Container status check
        - database: Database health check
        - events: Event capture check
        - config: Config validity check
        - pi_storage: PI System storage check
        - timestamp: Check timestamp (ISO format)
    """
    container = check_container_status()
    database = check_database_health()
    events = check_event_capture()
    config = check_config_validity()
    pi_storage = check_pi_system_storage()

    # Determine overall status
    statuses = [
        container.get("status"),
        database.get("status"),
        events.get("status"),
        config.get("status"),
        pi_storage.get("status"),
    ]

    if all(s in ("healthy", "active", "valid") for s in statuses):
        overall = "healthy"
    elif any(
        s in ("error", "unhealthy", "invalid", "locked", "read_only") for s in statuses
    ):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {
        "overall": overall,
        "container": container,
        "database": database,
        "events": events,
        "config": config,
        "pi_storage": pi_storage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
