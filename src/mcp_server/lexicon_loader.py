"""
Guidance Trigger Lexicon Loader

Feature: - Guidance Trigger Lexicon System
Durian Version: 0.6.3+

Loads lexicon entries from YAML files and compiles them for efficient matching.
Integrates with context disambiguation for ambiguous patterns.

Usage:
    loader = LexiconLoader()
    loader.load_from_directory("lexicon/")

    # Match against a message
    result = loader.match(message)
    if result.has_guidance:
        print(f"Detected: {result.primary_type}")
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from mcp_server.context_disambiguation import (
    LexiconEntry,
    ContextRule,
    DisambiguationResult,
    MatchResult,
    match_all_entries,
    format_disambiguation_log,
)

logger = logging.getLogger(__name__)


@dataclass
class LexiconStats:
    """Statistics about loaded lexicon."""

    total_entries: int = 0
    explicit_entries: int = 0
    implicit_entries: int = 0
    entries_with_context: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    sources: Dict[str, int] = field(default_factory=dict)


class LexiconLoader:
    """
    Loads and manages guidance trigger lexicon from YAML files.

    Architecture:
    - YAML files are source of truth (human-editable)
    - Compiled to regex patterns at load time
    - Context disambiguation applied at match time

    Thread Safety:
    - Load operations are not thread-safe
    - Match operations are thread-safe after loading
    """

    def __init__(self):
        self._entries: List[LexiconEntry] = []
        self._stats: LexiconStats = LexiconStats()
        self._loaded = False

        # Category defaults from schema
        self._category_defaults: Dict[str, float] = {}

    @property
    def entries(self) -> List[LexiconEntry]:
        """Get all loaded entries."""
        return self._entries

    @property
    def stats(self) -> LexiconStats:
        """Get loading statistics."""
        return self._stats

    @property
    def is_loaded(self) -> bool:
        """Whether lexicon has been loaded."""
        return self._loaded

    def load_schema(self, schema_path: Path) -> None:
        """
        Load schema file to get category defaults.

        Args:
            schema_path: Path to schema.yaml file
        """
        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return

        with open(schema_path, 'r') as f:
            schema = yaml.safe_load(f)

        # Extract category default confidences
        if 'categories' in schema:
            for category, config in schema['categories'].items():
                if isinstance(config, dict) and 'default_confidence' in config:
                    self._category_defaults[category] = config['default_confidence']

        logger.debug(f"Loaded schema with {len(self._category_defaults)} category defaults")

    def load_from_file(self, path: Path) -> int:
        """
        Load entries from a single YAML file.

        Args:
            path: Path to lexicon YAML file

        Returns:
            Number of entries loaded
        """
        if not path.exists():
            logger.warning(f"Lexicon file not found: {path}")
            return 0

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        if not data or 'entries' not in data:
            logger.warning(f"No entries found in {path}")
            return 0

        count = 0
        for entry_data in data['entries']:
            try:
                entry = self._parse_entry(entry_data)
                if entry:
                    self._entries.append(entry)
                    self._update_stats(entry)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to parse entry {entry_data.get('id', '?')}: {e}")

        logger.info(f"Loaded {count} entries from {path.name}")
        return count

    def load_from_directory(self, directory: Path) -> int:
        """
        Load all lexicon YAML files from a directory.

        Args:
            directory: Path to lexicon directory

        Returns:
            Total number of entries loaded
        """
        if isinstance(directory, str):
            directory = Path(directory)

        if not directory.exists():
            logger.error(f"Lexicon directory not found: {directory}")
            return 0

        # Load schema first
        schema_path = directory / "schema.yaml"
        self.load_schema(schema_path)

        # Load all YAML files (except schema)
        total = 0
        for yaml_file in sorted(directory.glob("*.yaml")):
            if yaml_file.name == "schema.yaml":
                continue
            total += self.load_from_file(yaml_file)

        self._loaded = total > 0
        self._stats.total_entries = total

        logger.info(
            f"Lexicon loaded: {total} entries, "
            f"{self._stats.explicit_entries} explicit, "
            f"{self._stats.implicit_entries} implicit, "
            f"{self._stats.entries_with_context} with context rules"
        )

        return total

    def _parse_entry(self, data: Dict[str, Any]) -> Optional[LexiconEntry]:
        """Parse a single entry from YAML data."""
        # Required fields
        if not all(k in data for k in ['id', 'pattern', 'category', 'guidance_type']):
            logger.warning(f"Entry missing required fields: {data}")
            return None

        # Get confidence (from entry, category default, or fallback)
        confidence = data.get('confidence')
        if confidence is None:
            confidence = self._category_defaults.get(data['category'], 0.75)

        # Parse context rule if present
        context_rule = None
        if 'context' in data:
            context_rule = ContextRule.from_dict(data['context'])

        # Compile pattern
        try:
            pattern_flags = re.IGNORECASE
            if data.get('case_sensitive', False):
                pattern_flags = 0
            pattern = re.compile(data['pattern'], pattern_flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern in {data['id']}: {e}")
            return None

        return LexiconEntry(
            id=data['id'],
            pattern=pattern,
            category=data['category'],
            guidance_type=data['guidance_type'],
            confidence=confidence,
            context_rule=context_rule,
            imp_feature=data.get('imp_feature', 'IMP-013'),
            source=data.get('source', 'system'),
            notes=data.get('notes', ''),
        )

    def _update_stats(self, entry: LexiconEntry) -> None:
        """Update statistics with a new entry."""
        if entry.guidance_type == 'explicit':
            self._stats.explicit_entries += 1
        else:
            self._stats.implicit_entries += 1

        if entry.context_rule is not None:
            self._stats.entries_with_context += 1

        self._stats.categories[entry.category] = \
            self._stats.categories.get(entry.category, 0) + 1

        self._stats.sources[entry.source] = \
            self._stats.sources.get(entry.source, 0) + 1

    def match(self, message: str) -> MatchResult:
        """
        Match message against all lexicon entries.

        Args:
            message: User message to check

        Returns:
            MatchResult with all matches and guidance type
        """
        if not self._loaded:
            logger.warning("Lexicon not loaded, returning empty result")
            return MatchResult()

        return match_all_entries(self._entries, message)

    def get_entries_by_category(self, category: str) -> List[LexiconEntry]:
        """Get all entries in a category."""
        return [e for e in self._entries if e.category == category]

    def get_entries_by_type(self, guidance_type: str) -> List[LexiconEntry]:
        """Get all entries of a guidance type."""
        return [e for e in self._entries if e.guidance_type == guidance_type]


# =============================================================================
# Module-level singleton for convenience
# =============================================================================

_default_loader: Optional[LexiconLoader] = None


def get_lexicon_loader() -> LexiconLoader:
    """Get the default lexicon loader (singleton)."""
    global _default_loader
    if _default_loader is None:
        _default_loader = LexiconLoader()
    return _default_loader


def load_default_lexicon(directory: Optional[Path] = None) -> int:
    """
    Load the default lexicon from the standard location.

    Args:
        directory: Optional override for lexicon directory

    Returns:
        Number of entries loaded
    """
    if directory is None:
        # Default to lexicon/ relative to this file
        directory = Path(__file__).parent / "lexicon"

    loader = get_lexicon_loader()
    return loader.load_from_directory(directory)


# =============================================================================
# UNIT TESTS
# =============================================================================

def run_tests():
    """Run unit tests for lexicon loader."""
    import tempfile
    import os

    print("Running lexicon loader tests...\n")

    # Create temp directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write test schema
        schema = """
schema_version: "1.0.0"
categories:
  test_category:
    default_confidence: 0.80
"""
        (tmpdir / "schema.yaml").write_text(schema)

        # Write test lexicon
        lexicon = """
entries:
  - id: test_001
    pattern: "from\\\\s+now\\\\s+on"
    category: test_category
    guidance_type: explicit
    confidence: 0.95

  - id: test_002
    pattern: "let'?s\\\\s+run"
    category: test_category
    guidance_type: explicit
    context:
      positive_markers:
        pattern: "\\\\b(tests?|builds?)\\\\b"
        weight: 0.15
      negative_markers:
        pattern: "\\\\b(see|away)\\\\b"
        weight: -0.30
      disambiguation_threshold: 0.60
      fallback_type: none
"""
        (tmpdir / "test.yaml").write_text(lexicon)

        # Test loading
        loader = LexiconLoader()
        count = loader.load_from_directory(tmpdir)

        assert count == 2, f"Expected 2 entries, got {count}"
        assert loader.stats.explicit_entries == 2
        assert 'test_category' in loader.stats.categories
        print(f"PASS: Loaded {count} entries")

        # Test matching
        result = loader.match("From now on, always run tests")
        assert result.has_guidance, "Should detect guidance"
        assert len(result.explicit_matches) >= 1
        print(f"PASS: Matched explicit guidance (confidence={result.highest_confidence_match.final_confidence:.2f})")

        # Test disambiguation - positive context
        result = loader.match("Let's run the tests")
        assert result.has_guidance, "Should detect guidance with positive context"
        print("PASS: Positive context disambiguation")

        # Test disambiguation - negative context
        result = loader.match("Let's run away")
        assert not result.has_guidance, "Should NOT detect guidance with negative context"
        print("PASS: Negative context disambiguation")

        # Test no match
        result = loader.match("Just a regular message")
        assert not result.has_guidance, "Should not detect guidance"
        print("PASS: No false positive")

    print("\nAll lexicon loader tests passed!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    run_tests()
