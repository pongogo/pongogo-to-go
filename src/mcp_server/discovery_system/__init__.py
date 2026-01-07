"""Discovery System - Repository Knowledge Discovery and Promotion

This module provides database-backed discovery of existing repository knowledge
(CLAUDE.md, wiki/, docs/) and observation-driven promotion to instruction files.

Architecture:
- Unified database at .pongogo/pongogo.db (schema v3.0.0)
- Tables: artifact_discovered, artifact_implemented
- Script-based scanning during pongogo init
- Observation-triggered promotion during routing
- CLI commands for discovery management

Usage:
    from discovery_system import DiscoverySystem

    ds = DiscoverySystem(project_root="/path/to/repo")

    # During init - scan and catalog
    result = ds.scan_repository()
    print(f"Found {result.total_discoveries} knowledge patterns")

    # During routing - check for matches
    matches = ds.find_matches(keywords=["authentication", "api"])
    for match in matches:
        if match.status == "DISCOVERED":
            ds.promote(match.id)  # Auto-create instruction file

    # CLI operations
    discoveries = ds.list_discoveries(status="DISCOVERED")
    ds.archive_discovery(discovery_id=5)
"""

from .operations import Discovery, DiscoverySystem, ScanResult
from .scanner import DiscoveredSection, DiscoveryScanner

__all__ = [
    "Discovery",
    "DiscoveredSection",
    "DiscoveryScanner",
    "DiscoverySystem",
    "ScanResult",
]

__version__ = "0.2.0"
