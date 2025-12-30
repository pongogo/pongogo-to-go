"""PI System - Potential Improvements Database and Management

This module provides database-backed management of Potential Improvements (PIs),
enabling structured tracking, relationship mapping, and automated gardening queries.

Architecture:
- SQLite database for metadata, relationships, and queries
- Markdown files remain source of truth for rich content
- Auto-sync between files and database
- Auto-generated index from database

Usage:
    from pi_system import PISystem

    pi = PISystem()
    pi.sync_from_files()  # Parse markdown → update DB

    # Queries
    stale = pi.find_stale(days=90)
    duplicates = pi.find_duplicates()
    ready = pi.find_ready_for_implementation()

    # Operations
    pi.add_evidence("PI-001", "", "Third occurrence identified")
    pi.add_relationship("PI-022", "PI-030", "RELATED", "Both address automation")

    # Generate index
    pi.generate_index()  # Creates potential_improvements.md
"""

from .database import PIDatabase
from .models import PIEvidence, PIRelationship, PotentialImprovement
from .operations import PISystem
from .queries import PIQueries

__all__ = [
    "PIDatabase",
    "PotentialImprovement",
    "PIEvidence",
    "PIRelationship",
    "PISystem",
    "PIQueries",
]

__version__ = "0.1.0"
