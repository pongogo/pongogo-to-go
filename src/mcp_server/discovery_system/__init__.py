"""Discovery System - Repository Knowledge Discovery and Promotion

This module provides database-backed discovery of existing repository knowledge
(CLAUDE.md, wiki/, docs/) and observation-driven promotion to instruction files.

Architecture:
- SQLite database for discovery catalog (.pongogo/discovery.db)
- Script-based scanning during pongogo init
- Observation-triggered promotion during routing
- CLI commands for discovery management

Usage:
    from discovery_system import DiscoverySystem

    ds = DiscoverySystem(project_root="/path/to/repo")

    # During init - scan and catalog
    summary = ds.scan_repository()
    print(f"Found {summary['total']} knowledge patterns")

    # During routing - check for matches
    matches = ds.find_matches(keywords=["authentication", "api"])
    for match in matches:
        if match.status == "DISCOVERED":
            ds.promote(match.id)  # Auto-create instruction file

    # CLI operations
    discoveries = ds.list_discoveries(status="DISCOVERED")
    ds.archive_discovery(discovery_id=5)
"""

from .database import DiscoveryDatabase
from .operations import DiscoverySystem
from .scanner import DiscoveryScanner

__all__ = [
    "DiscoveryDatabase",
    "DiscoveryScanner",
    "DiscoverySystem",
]

__version__ = "0.1.0"
