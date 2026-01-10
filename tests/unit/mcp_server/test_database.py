"""Tests for unified database module (schema v3.0.0)."""

import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

from mcp_server.database import (
    ArtifactStatus,
    GuidanceType,
    ObservationType,
    PongogoDatabase,
    SourceType,
    TriggerType,
    get_artifact_stats,
    get_artifacts_by_status,
    get_default_db_path,
    get_event_stats,
    get_observation_stats,
    get_observations_by_status,
    get_recent_events,
    get_trigger_stats,
    get_triggers_by_type,
    store_artifact_discovery,
    store_observation,
    store_routing_event,
    upsert_trigger,
)


class TestGetDefaultDbPath:
    """Tests for get_default_db_path function."""

    def test_returns_path(self):
        """Should return a Path object."""
        with patch.dict(os.environ, {}, clear=True):
            path = get_default_db_path()
        assert isinstance(path, Path)

    def test_user_level_fallback_no_env(self, tmp_path):
        """Without env vars and no .pongogo dir, falls back to ~/.pongogo/pongogo.db."""
        # Clear env vars and mock cwd to tmp_path (which has no .pongogo)
        with patch.dict(os.environ, {}, clear=True):
            with patch("mcp_server.config.Path.cwd", return_value=tmp_path):
                path = get_default_db_path()
        assert path == Path.home() / ".pongogo" / "pongogo.db"

    def test_project_local_explicit(self, tmp_path):
        """With explicit project root, should use .pongogo/pongogo.db."""
        path = get_default_db_path(project_root=tmp_path)
        assert path == tmp_path / ".pongogo" / "pongogo.db"

    def test_derives_from_knowledge_path(self, tmp_path):
        """Derives db path from PONGOGO_KNOWLEDGE_PATH (container deployment)."""
        # Simulate: /project/.pongogo/instructions -> /project/.pongogo/pongogo.db
        pongogo_dir = tmp_path / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(instructions_dir)},
            clear=True,
        ):
            path = get_default_db_path()

        assert path == pongogo_dir / "pongogo.db"

    def test_container_path_resolution(self, tmp_path):
        """Simulates container deployment database path resolution.

        Container scenario:
        - WORKDIR=/app (Python runs here)
        - Volume: host/.pongogo -> /project/.pongogo
        - PONGOGO_KNOWLEDGE_PATH=/project/.pongogo/instructions
        - Expected db path: /project/.pongogo/pongogo.db
        """
        # Create simulated container structure
        project_dir = tmp_path / "project"
        pongogo_dir = project_dir / ".pongogo"
        instructions_dir = pongogo_dir / "instructions"
        instructions_dir.mkdir(parents=True)

        with patch.dict(
            os.environ,
            {"PONGOGO_KNOWLEDGE_PATH": str(instructions_dir)},
            clear=True,
        ):
            path = get_default_db_path()

        # Database should be in the same .pongogo directory as instructions
        assert path == pongogo_dir / "pongogo.db"
        # NOT in ~/.pongogo or /app/.pongogo


class TestPongogoDatabase:
    """Tests for PongogoDatabase class."""

    def test_creates_database(self, tmp_path):
        """Should create database file."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        PongogoDatabase(db_path=db_path)
        assert db_path.exists()

    def test_creates_schema(self, tmp_path):
        """Should create all schema tables."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        PongogoDatabase(db_path=db_path)

        expected_tables = [
            "routing_events",
            "routing_triggers",
            "artifact_discovered",
            "artifact_implemented",
            "observation_discovered",
            "observation_implemented",
            "scan_history",
            "schema_info",
            "guidance_fulfillment",  # Added in schema v3.1.0 (Issue #390 Phase 9)
        ]

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"

    def test_schema_version(self, tmp_path):
        """Should set schema version to 3.1.0."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        version = db.get_schema_version()
        assert version == "3.1.0"  # Updated for Issue #390 Phase 9

    def test_get_stats(self, tmp_path):
        """Should return database statistics."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"
        db = PongogoDatabase(db_path=db_path)

        stats = db.get_stats()
        assert "schema_version" in stats
        assert "database_path" in stats
        assert "routing_events_count" in stats


class TestRoutingEvents:
    """Tests for routing event functions."""

    def test_store_event(self, tmp_path):
        """Should store routing event."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        result = store_routing_event(
            user_message="How do I create an epic?",
            routed_instructions=["epic_management", "task_basics"],
            engine_version="durian-0.6.1",
            db_path=db_path,
        )
        assert result is True

    def test_store_event_with_context(self, tmp_path):
        """Should store event with context."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        result = store_routing_event(
            user_message="Fix the bug",
            routed_instructions=["debugging"],
            engine_version="durian-0.6.1",
            context={"branch": "main", "files": ["src/app.py"]},
            session_id="test-session",
            routing_latency_ms=42.5,
            db_path=db_path,
        )
        assert result is True

    def test_get_stats_empty(self, tmp_path):
        """Should report status=missing when no database."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        stats = get_event_stats(db_path=db_path)
        # Database gets created on access, so it will be "empty"
        assert stats["status"] in ("missing", "empty")
        assert stats["total_count"] == 0

    def test_get_stats_with_events(self, tmp_path):
        """Should count events."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_routing_event("q1", ["i1"], "test", db_path=db_path)
        store_routing_event("q2", ["i2"], "test", db_path=db_path)
        store_routing_event("q3", ["i3"], "test", db_path=db_path)

        stats = get_event_stats(db_path=db_path)
        assert stats["status"] == "active"
        assert stats["total_count"] == 3

    def test_get_recent_events(self, tmp_path):
        """Should return recent events."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_routing_event("q1", ["i1"], "test", db_path=db_path)
        store_routing_event("q2", ["i2"], "test", db_path=db_path)

        events = get_recent_events(limit=10, db_path=db_path)
        assert len(events) == 2


class TestRoutingTriggers:
    """Tests for routing trigger functions."""

    def test_upsert_trigger(self, tmp_path):
        """Should insert trigger."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        row_id = upsert_trigger(
            trigger_type=TriggerType.FRICTION,
            trigger_key="oops",
            trigger_value="mistake_recovery",
            db_path=db_path,
        )
        assert row_id > 0

    def test_get_triggers_by_type(self, tmp_path):
        """Should retrieve triggers by type."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        upsert_trigger(TriggerType.FRICTION, "oops", "recovery", db_path=db_path)
        upsert_trigger(TriggerType.FRICTION, "mistake", "recovery", db_path=db_path)
        upsert_trigger(TriggerType.GUIDANCE_EXPLICIT, "always", "rule", db_path=db_path)

        friction = get_triggers_by_type(TriggerType.FRICTION, db_path=db_path)
        assert len(friction) == 2
        assert "oops" in friction
        assert "mistake" in friction

    def test_trigger_stats(self, tmp_path):
        """Should return trigger statistics."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        upsert_trigger(TriggerType.FRICTION, "oops", "recovery", db_path=db_path)

        stats = get_trigger_stats(db_path=db_path)
        assert "by_type" in stats
        assert TriggerType.FRICTION.value in stats["by_type"]


class TestArtifacts:
    """Tests for artifact discovery functions."""

    def test_store_artifact(self, tmp_path):
        """Should store discovered artifact."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        row_id = store_artifact_discovery(
            source_file="CLAUDE.md",
            source_type=SourceType.CLAUDE_MD,
            section_content="## Git Safety\n\nAlways use branches.",
            section_title="Git Safety",
            db_path=db_path,
        )
        assert row_id is not None
        assert row_id > 0

    def test_deduplication(self, tmp_path):
        """Should skip duplicate content."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        row_id1 = store_artifact_discovery(
            source_file="CLAUDE.md",
            source_type=SourceType.CLAUDE_MD,
            section_content="Same content",
            db_path=db_path,
        )
        row_id2 = store_artifact_discovery(
            source_file="wiki/Guide.md",
            source_type=SourceType.WIKI,
            section_content="Same content",  # Same content
            db_path=db_path,
        )

        assert row_id1 is not None
        assert row_id2 is None  # Duplicate

    def test_get_artifacts_by_status(self, tmp_path):
        """Should retrieve artifacts by status."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_artifact_discovery(
            "CLAUDE.md", SourceType.CLAUDE_MD, "Content 1", db_path=db_path
        )
        store_artifact_discovery(
            "wiki/A.md", SourceType.WIKI, "Content 2", db_path=db_path
        )

        artifacts = get_artifacts_by_status(ArtifactStatus.DISCOVERED, db_path=db_path)
        assert len(artifacts) == 2

    def test_artifact_stats(self, tmp_path):
        """Should return artifact statistics."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_artifact_discovery(
            "CLAUDE.md", SourceType.CLAUDE_MD, "Content", db_path=db_path
        )

        stats = get_artifact_stats(db_path=db_path)
        assert "by_status" in stats
        assert "by_source" in stats


class TestObservations:
    """Tests for observation discovery functions."""

    def test_store_observation(self, tmp_path):
        """Should store discovered observation."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        row_id = store_observation(
            observation_type=ObservationType.GUIDANCE_EXPLICIT,
            observation_content="Always run tests before committing",
            guidance_type=GuidanceType.EXPLICIT,
            db_path=db_path,
        )
        assert row_id > 0

    def test_get_observations_by_status(self, tmp_path):
        """Should retrieve observations by status."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_observation(
            ObservationType.GUIDANCE_EXPLICIT,
            "Rule 1",
            db_path=db_path,
        )
        store_observation(
            ObservationType.GUIDANCE_IMPLICIT,
            "Preference 1",
            db_path=db_path,
        )

        from mcp_server.database.observations import ObservationStatus

        observations = get_observations_by_status(
            ObservationStatus.DISCOVERED, db_path=db_path
        )
        assert len(observations) == 2

    def test_observation_stats(self, tmp_path):
        """Should return observation statistics."""
        db_path = tmp_path / ".pongogo" / "pongogo.db"

        store_observation(
            ObservationType.GUIDANCE_EXPLICIT,
            "Rule",
            guidance_type=GuidanceType.EXPLICIT,
            db_path=db_path,
        )

        stats = get_observation_stats(db_path=db_path)
        assert "by_status" in stats
        assert "by_type" in stats
        assert "by_guidance" in stats
