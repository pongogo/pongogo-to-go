"""
Pongogo Unified Database Module

Provides a single database for all routing-related data:
- routing_events: Event logging
- routing_triggers: Friction/guidance dictionaries
- artifact_discovered/implemented: File-based knowledge lifecycle
- observation_discovered/implemented: Runtime observation lifecycle

Database location: .pongogo/pongogo.db (project root)

Shared schema between Super Pongogo and pongogo-to-go.
Reference: docs/observability/unified_schema_v3.sql (Super Pongogo)
"""

from .artifacts import (
    ArtifactStatus,
    SourceType,
    archive_artifact,
    get_artifact_stats,
    get_artifacts_by_status,
    promote_artifact,
    store_artifact_discovery,
)
from .database import SCHEMA_VERSION, PongogoDatabase, get_default_db_path
from .events import get_event_stats, get_recent_events, store_routing_event
from .observations import (
    GuidanceType,
    ImplementationType,
    ObservationStatus,
    ObservationType,
    get_observation_stats,
    get_observations_by_status,
    promote_observation,
    reject_observation,
    store_observation,
)
from .triggers import (
    TriggerType,
    bulk_load_triggers,
    get_trigger_stats,
    get_triggers_by_type,
    upsert_trigger,
)

__all__ = [
    # Database
    "PongogoDatabase",
    "get_default_db_path",
    "SCHEMA_VERSION",
    # Events
    "store_routing_event",
    "get_event_stats",
    "get_recent_events",
    # Triggers
    "get_triggers_by_type",
    "upsert_trigger",
    "bulk_load_triggers",
    "get_trigger_stats",
    "TriggerType",
    # Artifacts
    "store_artifact_discovery",
    "promote_artifact",
    "get_artifacts_by_status",
    "archive_artifact",
    "get_artifact_stats",
    "ArtifactStatus",
    "SourceType",
    # Observations
    "store_observation",
    "promote_observation",
    "reject_observation",
    "get_observations_by_status",
    "get_observation_stats",
    "ObservationType",
    "GuidanceType",
    "ObservationStatus",
    "ImplementationType",
]
