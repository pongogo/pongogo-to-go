"""
Unified Lexicon Database Module

Task: #511 - Migrate Lexicon System to Database
Parent: #488 - Guidance Trigger Lexicon System

This module provides database-backed storage for both guidance and friction
lexicon entries, replacing the previous YAML-based system.

Architecture:
- SQLite database for lexicon entries
- Same LexiconEntry interface as YAML loader (drop-in replacement)
- Context disambiguation via positive/negative patterns
- GT event provenance tracking for pattern analytics

Usage:
    from lexicon_db import LexiconDB, load_lexicon_from_db

    # Load all entries
    db = LexiconDB()
    entries = db.get_all_entries()

    # Load by type
    guidance_entries = db.get_entries_by_type("guidance")
    friction_entries = db.get_entries_by_type("friction")

    # Match against message (using context_disambiguation)
    from mcp_server.context_disambiguation import match_all_entries
    result = match_all_entries(entries, message)
"""

import contextlib
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from mcp_server.context_disambiguation import ContextRule, LexiconEntry

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent / "lexicon.db"

# Schema version for migrations
# v1: Initial schema (guidance, friction)
# v2: Added 'hedging' lexicon_type (Issue #524)
SCHEMA_VERSION = 2


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

SCHEMA_SQL = """
-- Unified lexicon entries table
-- Supports guidance (IMP-013), friction (IMP-011), and hedging (Issue #524) patterns
CREATE TABLE IF NOT EXISTS lexicon_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT UNIQUE NOT NULL,  -- e.g., "explicit_001", "friction_correction_042", "hedging_001"

    -- Pattern matching
    pattern TEXT NOT NULL,
    pattern_flags INTEGER DEFAULT 2,  -- re.IGNORECASE = 2

    -- Classification
    lexicon_type TEXT NOT NULL CHECK (lexicon_type IN ('guidance', 'friction', 'hedging')),
    category TEXT NOT NULL,  -- e.g., "future_directive", "correction", "retry", "uncertainty_modal"
    sub_type TEXT,  -- guidance: "explicit"/"implicit"; friction: "correction"/"retry"/"rejection"/"refinement"; hedging: null

    -- Confidence scoring
    base_confidence REAL DEFAULT 0.75,

    -- Context disambiguation (optional)
    positive_pattern TEXT,  -- regex for positive context markers
    positive_weight REAL DEFAULT 0.0,
    negative_pattern TEXT,  -- regex for negative context markers
    negative_weight REAL DEFAULT 0.0,  -- should be negative value
    disambiguation_threshold REAL DEFAULT 0.5,
    fallback_type TEXT DEFAULT 'none' CHECK (fallback_type IN ('none', 'implicit')),

    -- Provenance tracking
    source TEXT DEFAULT 'system' CHECK (source IN ('system', 'gt_v4', 'gt_v3', 'user', 'migration')),
    source_event_ids TEXT,  -- JSON array of GT event IDs that inspired this pattern
    imp_feature TEXT DEFAULT 'IMP-013',
    notes TEXT,

    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    enabled INTEGER DEFAULT 1  -- boolean: 1=enabled, 0=disabled
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_lexicon_type ON lexicon_entries(lexicon_type);
CREATE INDEX IF NOT EXISTS idx_lexicon_category ON lexicon_entries(category);
CREATE INDEX IF NOT EXISTS idx_lexicon_sub_type ON lexicon_entries(sub_type);
CREATE INDEX IF NOT EXISTS idx_lexicon_enabled ON lexicon_entries(enabled);
CREATE INDEX IF NOT EXISTS idx_lexicon_source ON lexicon_entries(source);

-- Pattern match statistics (optional, for analytics)
CREATE TABLE IF NOT EXISTS lexicon_match_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    match_count INTEGER DEFAULT 0,
    last_matched_at TEXT,
    true_positives INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    FOREIGN KEY (entry_id) REFERENCES lexicon_entries(entry_id)
);

CREATE INDEX IF NOT EXISTS idx_match_stats_entry ON lexicon_match_stats(entry_id);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


# =============================================================================
# DATABASE CLASS
# =============================================================================


class LexiconDB:
    """
    Database-backed lexicon storage and retrieval.

    Thread Safety:
    - Read operations are thread-safe (each call creates new connection)
    - Write operations should be serialized by caller
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize lexicon database.

        Args:
            db_path: Path to SQLite database. Defaults to lexicon.db in module dir.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create schema if it doesn't exist, run migrations if needed."""
        conn = self._get_connection()
        try:
            conn.executescript(SCHEMA_SQL)

            # Check/set schema version
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row[0] else 0

            # Run migrations
            if current_version < 2:
                self._migrate_v1_to_v2(conn)

            if current_version < SCHEMA_VERSION:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )
                conn.commit()
                logger.info(f"Lexicon DB schema initialized (version {SCHEMA_VERSION})")
        finally:
            conn.close()

    def _migrate_v1_to_v2(self, conn: sqlite3.Connection) -> None:
        """
        Migrate from v1 to v2: Add 'hedging' to lexicon_type CHECK constraint.

        SQLite doesn't support ALTER TABLE for CHECK constraints, so we:
        1. Create new table with updated constraint
        2. Copy all data
        3. Drop old table
        4. Rename new table
        """
        logger.info(
            "Migrating lexicon_entries from v1 to v2 (adding 'hedging' type)..."
        )

        # Check if old table exists and has data
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='lexicon_entries'"
        )
        if not cursor.fetchone():
            logger.info("No existing lexicon_entries table, skipping migration")
            return

        try:
            # Create new table with updated constraint
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lexicon_entries_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT UNIQUE NOT NULL,
                    pattern TEXT NOT NULL,
                    pattern_flags INTEGER DEFAULT 2,
                    lexicon_type TEXT NOT NULL CHECK (lexicon_type IN ('guidance', 'friction', 'hedging')),
                    category TEXT NOT NULL,
                    sub_type TEXT,
                    base_confidence REAL DEFAULT 0.75,
                    positive_pattern TEXT,
                    positive_weight REAL DEFAULT 0.0,
                    negative_pattern TEXT,
                    negative_weight REAL DEFAULT 0.0,
                    disambiguation_threshold REAL DEFAULT 0.5,
                    fallback_type TEXT DEFAULT 'none' CHECK (fallback_type IN ('none', 'implicit')),
                    source TEXT DEFAULT 'system' CHECK (source IN ('system', 'gt_v4', 'gt_v3', 'user', 'migration')),
                    source_event_ids TEXT,
                    imp_feature TEXT DEFAULT 'IMP-013',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    enabled INTEGER DEFAULT 1
                )
            """)

            # Copy data from old table
            conn.execute("""
                INSERT INTO lexicon_entries_v2
                SELECT * FROM lexicon_entries
            """)

            # Drop old table
            conn.execute("DROP TABLE lexicon_entries")

            # Rename new table
            conn.execute("ALTER TABLE lexicon_entries_v2 RENAME TO lexicon_entries")

            # Recreate indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lexicon_type ON lexicon_entries(lexicon_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lexicon_category ON lexicon_entries(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lexicon_sub_type ON lexicon_entries(sub_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lexicon_enabled ON lexicon_entries(enabled)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lexicon_source ON lexicon_entries(source)"
            )

            conn.commit()
            logger.info("Migration v1->v2 complete: 'hedging' type now supported")

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Migration v1->v2 failed: {e}")
            raise

    def get_all_entries(self, enabled_only: bool = True) -> list[LexiconEntry]:
        """
        Get all lexicon entries.

        Args:
            enabled_only: If True, only return enabled entries.

        Returns:
            List of LexiconEntry objects ready for matching.
        """
        conn = self._get_connection()
        try:
            query = "SELECT * FROM lexicon_entries"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY lexicon_type, category, entry_id"

            cursor = conn.execute(query)
            return [self._row_to_entry(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_entries_by_type(
        self, lexicon_type: str, enabled_only: bool = True
    ) -> list[LexiconEntry]:
        """
        Get entries by lexicon type (guidance or friction).

        Args:
            lexicon_type: "guidance" or "friction"
            enabled_only: If True, only return enabled entries.

        Returns:
            List of LexiconEntry objects.
        """
        conn = self._get_connection()
        try:
            query = "SELECT * FROM lexicon_entries WHERE lexicon_type = ?"
            params: list[Any] = [lexicon_type]
            if enabled_only:
                query += " AND enabled = 1"
            query += " ORDER BY category, entry_id"

            cursor = conn.execute(query, params)
            return [self._row_to_entry(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_entries_by_category(
        self, category: str, enabled_only: bool = True
    ) -> list[LexiconEntry]:
        """Get entries by category."""
        conn = self._get_connection()
        try:
            query = "SELECT * FROM lexicon_entries WHERE category = ?"
            params: list[Any] = [category]
            if enabled_only:
                query += " AND enabled = 1"

            cursor = conn.execute(query, params)
            return [self._row_to_entry(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_entry_by_id(self, entry_id: str) -> LexiconEntry | None:
        """Get a single entry by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM lexicon_entries WHERE entry_id = ?", (entry_id,)
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    def insert_entry(
        self,
        entry_id: str,
        pattern: str,
        lexicon_type: str,
        category: str,
        sub_type: str | None = None,
        base_confidence: float = 0.75,
        positive_pattern: str | None = None,
        positive_weight: float = 0.0,
        negative_pattern: str | None = None,
        negative_weight: float = 0.0,
        disambiguation_threshold: float = 0.5,
        fallback_type: str = "none",
        source: str = "system",
        source_event_ids: list[int] | None = None,
        imp_feature: str = "IMP-013",
        notes: str = "",
        enabled: bool = True,
    ) -> bool:
        """
        Insert a new lexicon entry.

        Returns:
            True if inserted, False if entry_id already exists.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO lexicon_entries (
                    entry_id, pattern, lexicon_type, category, sub_type,
                    base_confidence, positive_pattern, positive_weight,
                    negative_pattern, negative_weight, disambiguation_threshold,
                    fallback_type, source, source_event_ids, imp_feature, notes, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    pattern,
                    lexicon_type,
                    category,
                    sub_type,
                    base_confidence,
                    positive_pattern,
                    positive_weight,
                    negative_pattern,
                    negative_weight,
                    disambiguation_threshold,
                    fallback_type,
                    source,
                    json.dumps(source_event_ids) if source_event_ids else None,
                    imp_feature,
                    notes,
                    1 if enabled else 0,
                ),
            )
            conn.commit()
            logger.debug(f"Inserted lexicon entry: {entry_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Entry already exists: {entry_id}")
            return False
        finally:
            conn.close()

    def update_entry(self, entry_id: str, **kwargs) -> bool:
        """
        Update an existing entry.

        Args:
            entry_id: Entry to update
            **kwargs: Fields to update (pattern, confidence, etc.)

        Returns:
            True if updated, False if entry not found.
        """
        if not kwargs:
            return False

        # Build SET clause
        allowed_fields = {
            "pattern",
            "lexicon_type",
            "category",
            "sub_type",
            "base_confidence",
            "positive_pattern",
            "positive_weight",
            "negative_pattern",
            "negative_weight",
            "disambiguation_threshold",
            "fallback_type",
            "source",
            "source_event_ids",
            "imp_feature",
            "notes",
            "enabled",
        }

        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                if key == "source_event_ids" and isinstance(value, list):
                    value = json.dumps(value)
                elif key == "enabled":
                    value = 1 if value else 0
                values.append(value)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(entry_id)

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"UPDATE lexicon_entries SET {', '.join(updates)} WHERE entry_id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM lexicon_entries WHERE entry_id = ?", (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get lexicon statistics."""
        conn = self._get_connection()
        try:
            stats = {}

            # Total counts
            cursor = conn.execute(
                "SELECT lexicon_type, COUNT(*) FROM lexicon_entries WHERE enabled = 1 GROUP BY lexicon_type"
            )
            for row in cursor.fetchall():
                stats[f"{row[0]}_count"] = row[1]

            # Category breakdown
            cursor = conn.execute(
                """
                SELECT lexicon_type, category, COUNT(*)
                FROM lexicon_entries WHERE enabled = 1
                GROUP BY lexicon_type, category
                """
            )
            stats["categories"] = {}
            for row in cursor.fetchall():
                key = f"{row[0]}:{row[1]}"
                stats["categories"][key] = row[2]

            # Source breakdown
            cursor = conn.execute(
                "SELECT source, COUNT(*) FROM lexicon_entries WHERE enabled = 1 GROUP BY source"
            )
            stats["sources"] = {row[0]: row[1] for row in cursor.fetchall()}

            # Entries with context rules
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM lexicon_entries
                WHERE enabled = 1 AND (positive_pattern IS NOT NULL OR negative_pattern IS NOT NULL)
                """
            )
            stats["with_context_rules"] = cursor.fetchone()[0]

            return stats
        finally:
            conn.close()

    def _row_to_entry(self, row: sqlite3.Row) -> LexiconEntry:
        """Convert database row to LexiconEntry object."""
        # Compile pattern
        pattern_flags = row["pattern_flags"] or re.IGNORECASE
        try:
            pattern = re.compile(row["pattern"], pattern_flags)
        except re.error as e:
            logger.error(f"Invalid pattern in {row['entry_id']}: {e}")
            # Return a pattern that never matches
            pattern = re.compile(r"(?!)")

        # Build context rule if present
        context_rule = None
        if row["positive_pattern"] or row["negative_pattern"]:
            positive_pattern = None
            if row["positive_pattern"]:
                with contextlib.suppress(re.error):
                    positive_pattern = re.compile(
                        row["positive_pattern"], re.IGNORECASE
                    )

            negative_pattern = None
            if row["negative_pattern"]:
                with contextlib.suppress(re.error):
                    negative_pattern = re.compile(
                        row["negative_pattern"], re.IGNORECASE
                    )

            context_rule = ContextRule(
                positive_pattern=positive_pattern,
                positive_weight=row["positive_weight"] or 0.0,
                negative_pattern=negative_pattern,
                negative_weight=row["negative_weight"] or 0.0,
                disambiguation_threshold=row["disambiguation_threshold"] or 0.5,
                fallback_type=row["fallback_type"] or "none",
            )

        return LexiconEntry(
            id=row["entry_id"],
            pattern=pattern,
            category=row["category"],
            guidance_type=row["sub_type"]
            or row["category"],  # sub_type for guidance, category for friction
            confidence=row["base_confidence"],
            context_rule=context_rule,
            imp_feature=row["imp_feature"] or "IMP-013",
            source=row["source"] or "system",
            notes=row["notes"] or "",
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_db: LexiconDB | None = None


def get_lexicon_db(db_path: Path | None = None) -> LexiconDB:
    """Get the default lexicon database (singleton)."""
    global _default_db
    if _default_db is None or db_path is not None:
        _default_db = LexiconDB(db_path)
    return _default_db


def load_lexicon_from_db(
    lexicon_type: str | None = None, db_path: Path | None = None
) -> list[LexiconEntry]:
    """
    Load lexicon entries from database.

    Args:
        lexicon_type: Optional filter ("guidance", "friction", or "hedging")
        db_path: Optional database path override

    Returns:
        List of LexiconEntry objects ready for matching.
    """
    db = get_lexicon_db(db_path)
    if lexicon_type:
        return db.get_entries_by_type(lexicon_type)
    return db.get_all_entries()


# =============================================================================
# HEDGING ENTRY SEEDING (Issue #524)
# =============================================================================

# Hedging entries with penalty values
# These patterns suppress implicit guidance when present
HEDGING_SEED_ENTRIES = [
    # Strong hedging indicators - penalty -0.40
    # These clearly indicate uncertainty/discussion, not rules
    {
        "entry_id": "hedging_001",
        "pattern": r"\bmaybe\b",
        "category": "uncertainty_modal",
        "base_confidence": -0.40,
        "notes": "Strong uncertainty indicator",
    },
    {
        "entry_id": "hedging_002",
        "pattern": r"\bpossibly\b",
        "category": "uncertainty_modal",
        "base_confidence": -0.40,
        "notes": "Strong uncertainty indicator",
    },
    {
        "entry_id": "hedging_003",
        "pattern": r"\bperhaps\b",
        "category": "uncertainty_modal",
        "base_confidence": -0.40,
        "notes": "Strong uncertainty indicator",
    },
    {
        "entry_id": "hedging_004",
        "pattern": r"\bshould\s+we\b",
        "category": "question_suggestion",
        "base_confidence": -0.40,
        "notes": "Question framing indicates discussion, not directive",
    },
    {
        "entry_id": "hedging_005",
        "pattern": r"\bcould\s+we\b",
        "category": "question_suggestion",
        "base_confidence": -0.40,
        "notes": "Question framing indicates discussion, not directive",
    },
    # Medium hedging indicators - penalty -0.35
    {
        "entry_id": "hedging_006",
        "pattern": r"\bmight\b",
        "category": "uncertainty_modal",
        "base_confidence": -0.35,
        "notes": "Medium uncertainty indicator",
    },
    {
        "entry_id": "hedging_007",
        "pattern": r"\bpotentially\b",
        "category": "uncertainty_modal",
        "base_confidence": -0.35,
        "notes": "Medium uncertainty indicator",
    },
    {
        "entry_id": "hedging_008",
        "pattern": r"\bcould\s+be\b",
        "category": "conditional_tentative",
        "base_confidence": -0.35,
        "notes": "Conditional language",
    },
    {
        "entry_id": "hedging_009",
        "pattern": r"\bmight\s+be\b",
        "category": "conditional_tentative",
        "base_confidence": -0.35,
        "notes": "Conditional language",
    },
    {
        "entry_id": "hedging_010",
        "pattern": r"\bwhat\s+if\b",
        "category": "conditional_tentative",
        "base_confidence": -0.35,
        "notes": "Hypothetical framing",
    },
    # Weak hedging indicators - penalty -0.30
    {
        "entry_id": "hedging_011",
        "pattern": r"\bi\s+wonder\b",
        "category": "conditional_tentative",
        "base_confidence": -0.30,
        "notes": "Weak uncertainty - musing aloud",
    },
    {
        "entry_id": "hedging_012",
        "pattern": r"\bwondering\s+if\b",
        "category": "conditional_tentative",
        "base_confidence": -0.30,
        "notes": "Weak uncertainty - musing aloud",
    },
    {
        "entry_id": "hedging_013",
        "pattern": r"\bnot\s+sure\s+if\b",
        "category": "conditional_tentative",
        "base_confidence": -0.30,
        "notes": "Explicit uncertainty acknowledgment",
    },
    {
        "entry_id": "hedging_014",
        "pattern": r"\bnot\s+certain\b",
        "category": "conditional_tentative",
        "base_confidence": -0.30,
        "notes": "Explicit uncertainty acknowledgment",
    },
    {
        "entry_id": "hedging_015",
        "pattern": r"\bwhat\s+do\s+you\s+think\b",
        "category": "question_suggestion",
        "base_confidence": -0.30,
        "notes": "Soliciting opinion, not giving directive",
    },
    {
        "entry_id": "hedging_016",
        "pattern": r"\bwould\s+it\s+make\s+sense\b",
        "category": "question_suggestion",
        "base_confidence": -0.30,
        "notes": "Soliciting opinion, not giving directive",
    },
]


def seed_hedging_entries(db: LexiconDB | None = None, force: bool = False) -> int:
    """
    Seed hedging entries into the lexicon database.

    Args:
        db: LexiconDB instance (uses default if None)
        force: If True, update existing entries. If False, skip existing.

    Returns:
        Number of entries inserted or updated.
    """
    if db is None:
        db = get_lexicon_db()

    count = 0
    for entry_data in HEDGING_SEED_ENTRIES:
        # Check if entry exists
        existing = db.get_entry_by_id(entry_data["entry_id"])

        if existing and not force:
            logger.debug(f"Skipping existing entry: {entry_data['entry_id']}")
            continue

        if existing and force:
            # Update existing
            success = db.update_entry(
                entry_data["entry_id"],
                pattern=entry_data["pattern"],
                category=entry_data["category"],
                base_confidence=entry_data["base_confidence"],
                notes=entry_data["notes"],
            )
            if success:
                count += 1
                logger.debug(f"Updated hedging entry: {entry_data['entry_id']}")
        else:
            # Insert new
            success = db.insert_entry(
                entry_id=entry_data["entry_id"],
                pattern=entry_data["pattern"],
                lexicon_type="hedging",
                category=entry_data["category"],
                base_confidence=entry_data["base_confidence"],
                source="system",
                imp_feature="IMP-524",  # Issue #524
                notes=entry_data["notes"],
            )
            if success:
                count += 1
                logger.debug(f"Inserted hedging entry: {entry_data['entry_id']}")

    logger.info(f"Seeded {count} hedging entries")
    return count


# =============================================================================
# UNIT TESTS
# =============================================================================


def run_tests():
    """Run unit tests for lexicon database."""
    import os
    import tempfile

    print("Running lexicon database tests...\n")

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db_path = Path(f.name)

    try:
        db = LexiconDB(test_db_path)

        # Test insert
        success = db.insert_entry(
            entry_id="test_001",
            pattern=r"from\s+now\s+on",
            lexicon_type="guidance",
            category="future_directive",
            sub_type="explicit",
            base_confidence=0.95,
            source="system",
        )
        assert success, "Insert should succeed"
        print("PASS: Insert entry")

        # Test duplicate insert
        success = db.insert_entry(
            entry_id="test_001",
            pattern=r"duplicate",
            lexicon_type="guidance",
            category="test",
        )
        assert not success, "Duplicate insert should fail"
        print("PASS: Duplicate rejected")

        # Test insert with context rule
        success = db.insert_entry(
            entry_id="test_002",
            pattern=r"let's\s+run",
            lexicon_type="guidance",
            category="imperative_lets",
            sub_type="explicit",
            base_confidence=0.55,
            positive_pattern=r"\b(tests?|builds?)\b",
            positive_weight=0.15,
            negative_pattern=r"\b(away|see)\b",
            negative_weight=-0.30,
            disambiguation_threshold=0.60,
            source="gt_v4",
            source_event_ids=[100, 200, 300],
        )
        assert success, "Insert with context should succeed"
        print("PASS: Insert with context rule")

        # Test friction entry
        success = db.insert_entry(
            entry_id="friction_001",
            pattern=r"we\s+already\s+(broke|did|have)",
            lexicon_type="friction",
            category="correction",
            sub_type="correction",
            base_confidence=0.50,
            positive_pattern=r"\b(you|your|you're)\b",
            positive_weight=0.30,
            negative_pattern=r"\b(out|phase|task)\b",
            negative_weight=-0.35,
            disambiguation_threshold=0.60,
            imp_feature="IMP-011",
            source="gt_v4",
            source_event_ids=[1782, 1824],
        )
        assert success, "Friction entry should succeed"
        print("PASS: Insert friction entry")

        # Test get all entries
        entries = db.get_all_entries()
        assert len(entries) == 3, f"Should have 3 entries, got {len(entries)}"
        print(f"PASS: Get all entries ({len(entries)})")

        # Test get by type
        guidance = db.get_entries_by_type("guidance")
        friction = db.get_entries_by_type("friction")
        assert len(guidance) == 2, f"Should have 2 guidance, got {len(guidance)}"
        assert len(friction) == 1, f"Should have 1 friction, got {len(friction)}"
        print(f"PASS: Get by type (guidance={len(guidance)}, friction={len(friction)})")

        # Test context rule loading
        entry = db.get_entry_by_id("test_002")
        assert entry is not None
        assert entry.context_rule is not None
        assert entry.context_rule.positive_pattern is not None
        print("PASS: Context rule loaded correctly")

        # Test matching with context (using context_disambiguation)
        from mcp_server.context_disambiguation import match_all_entries

        result = match_all_entries(entries, "From now on, always run tests first")
        assert result.has_guidance, "Should detect guidance"
        print("PASS: Pattern matching works")

        # Test positive context disambiguation
        result = match_all_entries(entries, "Let's run the tests")
        assert result.has_guidance, "Should detect with positive context"
        print("PASS: Positive context disambiguation")

        # Test negative context disambiguation
        result = match_all_entries(entries, "Let's run away")
        assert not result.has_guidance, "Should NOT detect with negative context"
        print("PASS: Negative context disambiguation")

        # Test stats
        stats = db.get_stats()
        assert stats.get("guidance_count") == 2
        assert stats.get("friction_count") == 1
        assert stats.get("with_context_rules") == 2
        print(f"PASS: Stats ({stats})")

        # Test update
        success = db.update_entry("test_001", base_confidence=0.99)
        assert success
        entry = db.get_entry_by_id("test_001")
        assert entry.confidence == 0.99
        print("PASS: Update entry")

        # Test delete
        success = db.delete_entry("test_001")
        assert success
        entry = db.get_entry_by_id("test_001")
        assert entry is None
        print("PASS: Delete entry")

        print("\nAll lexicon database tests passed!")

    finally:
        # Cleanup
        os.unlink(test_db_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    run_tests()
