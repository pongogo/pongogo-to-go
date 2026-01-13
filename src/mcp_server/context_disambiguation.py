"""
Context Disambiguation Module for Guidance Trigger Lexicon

Task: #492 - Implement context disambiguation
Parent: #488 - Guidance Trigger Lexicon System

This module implements context-aware disambiguation for ambiguous trigger patterns.
It uses positive/negative context markers to adjust confidence scores and determine
whether a pattern match should be treated as guidance.

Examples of disambiguation:
- "let's run the tests" → guidance (positive: "tests")
- "let's see what happens" → not guidance (negative: "see")
- "can you add a feature?" → guidance (positive: "add")
- "can you explain why?" → not guidance (negative: "explain")
"""

import logging
import re
from dataclasses import dataclass, field
from re import Match, Pattern
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class ContextRule:
    """Context disambiguation rule for a lexicon entry."""

    # Positive context (increases confidence)
    positive_pattern: Pattern | None = None
    positive_weight: float = 0.0

    # Negative context (decreases confidence)
    negative_pattern: Pattern | None = None
    negative_weight: float = 0.0  # Should be negative value

    # Thresholds
    disambiguation_threshold: float = 0.5

    # Fallback when below threshold
    fallback_type: str = "none"  # "none" | "implicit"

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional["ContextRule"]:
        """Create ContextRule from YAML dict format."""
        if not data:
            return None

        positive_pattern = None
        positive_weight = 0.0
        if pos := data.get("positive_markers"):
            if pattern := pos.get("pattern"):
                positive_pattern = re.compile(pattern, re.IGNORECASE)
            positive_weight = pos.get("weight", 0.15)

        negative_pattern = None
        negative_weight = 0.0
        if neg := data.get("negative_markers"):
            if pattern := neg.get("pattern"):
                negative_pattern = re.compile(pattern, re.IGNORECASE)
            negative_weight = neg.get("weight", -0.25)

        return cls(
            positive_pattern=positive_pattern,
            positive_weight=positive_weight,
            negative_pattern=negative_pattern,
            negative_weight=negative_weight,
            disambiguation_threshold=data.get("disambiguation_threshold", 0.5),
            fallback_type=data.get("fallback_type", "none"),
        )


@dataclass
class LexiconEntry:
    """Single lexicon entry with compiled pattern and context rules."""

    id: str
    pattern: Pattern
    category: str
    guidance_type: str  # "explicit" | "implicit"
    confidence: float
    context_rule: ContextRule | None = None
    imp_feature: str = "IMP-013"
    source: str = "system"
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "LexiconEntry":
        """Create LexiconEntry from YAML dict format."""
        return cls(
            id=data["id"],
            pattern=re.compile(data["pattern"], re.IGNORECASE),
            category=data["category"],
            guidance_type=data["guidance_type"],
            confidence=data.get("confidence", 0.8),
            context_rule=ContextRule.from_dict(data.get("context")),
            imp_feature=data.get("imp_feature", "IMP-013"),
            source=data.get("source", "system"),
            notes=data.get("notes", ""),
        )


@dataclass
class DisambiguationResult:
    """Result of context disambiguation."""

    # Whether the pattern matched at all
    pattern_matched: bool

    # The regex match object (if matched)
    match: Match | None = None

    # Entry that matched
    entry: LexiconEntry | None = None

    # Confidence scores
    base_confidence: float = 0.0
    context_adjustment: float = 0.0
    final_confidence: float = 0.0

    # Disambiguation details
    positive_triggered: bool = False
    negative_triggered: bool = False

    # Final decision
    should_trigger: bool = False
    final_guidance_type: str = "none"  # "explicit" | "implicit" | "none"

    # Observability
    disambiguation_reason: str = ""


# =============================================================================
# CORE DISAMBIGUATION LOGIC
# =============================================================================


def apply_context_disambiguation(
    entry: LexiconEntry,
    message: str,
    match: Match,
) -> DisambiguationResult:
    """
    Apply context disambiguation rules to a pattern match.

    Args:
        entry: The lexicon entry that matched
        message: The full message text
        match: The regex match object

    Returns:
        DisambiguationResult with confidence scores and final decision
    """
    result = DisambiguationResult(
        pattern_matched=True,
        match=match,
        entry=entry,
        base_confidence=entry.confidence,
    )

    # No context rule = always trigger with base confidence
    if not entry.context_rule:
        result.final_confidence = entry.confidence
        result.should_trigger = True
        result.final_guidance_type = entry.guidance_type
        result.disambiguation_reason = "no_context_rule"

        logger.debug(
            f"[{entry.id}] No context rule, triggering with confidence={entry.confidence:.2f}"
        )
        return result

    rule = entry.context_rule
    confidence = entry.confidence

    # Apply positive context markers
    if rule.positive_pattern:
        if rule.positive_pattern.search(message):
            confidence += rule.positive_weight
            result.positive_triggered = True
            logger.debug(
                f"[{entry.id}] Positive context matched, "
                f"adjustment={rule.positive_weight:+.2f}"
            )

    # Apply negative context markers
    if rule.negative_pattern:
        if rule.negative_pattern.search(message):
            confidence += rule.negative_weight  # negative_weight is already negative
            result.negative_triggered = True
            logger.debug(
                f"[{entry.id}] Negative context matched, "
                f"adjustment={rule.negative_weight:+.2f}"
            )

    # Clamp confidence to [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    result.context_adjustment = confidence - entry.confidence
    result.final_confidence = confidence

    # Decision based on threshold
    if confidence >= rule.disambiguation_threshold:
        result.should_trigger = True
        result.final_guidance_type = entry.guidance_type
        result.disambiguation_reason = "above_threshold"

        logger.debug(
            f"[{entry.id}] Confidence {confidence:.2f} >= threshold "
            f"{rule.disambiguation_threshold:.2f}, triggering as {entry.guidance_type}"
        )

    elif rule.fallback_type == "implicit" and not result.negative_triggered:
        # Only fallback to implicit if no negative context was found
        # If negative context pushed it below threshold, don't trigger at all
        result.should_trigger = True
        result.final_guidance_type = "implicit"
        result.disambiguation_reason = "fallback_to_implicit"

        logger.debug(
            f"[{entry.id}] Confidence {confidence:.2f} < threshold, "
            f"falling back to implicit (no negative context)"
        )

    else:
        result.should_trigger = False
        result.final_guidance_type = "none"

        if result.negative_triggered:
            result.disambiguation_reason = "negative_context_excluded"
            logger.debug(f"[{entry.id}] Negative context triggered, not triggering")
        else:
            result.disambiguation_reason = "below_threshold"
            logger.debug(
                f"[{entry.id}] Confidence {confidence:.2f} < threshold "
                f"{rule.disambiguation_threshold:.2f}, not triggering"
            )

    return result


def match_with_disambiguation(
    entry: LexiconEntry,
    message: str,
) -> DisambiguationResult:
    """
    Attempt to match a lexicon entry against a message with disambiguation.

    Args:
        entry: The lexicon entry to match
        message: The message text to check

    Returns:
        DisambiguationResult with match details and final decision
    """
    # First check if pattern matches at all
    match = entry.pattern.search(message)

    if not match:
        return DisambiguationResult(
            pattern_matched=False,
            entry=entry,
            disambiguation_reason="pattern_not_matched",
        )

    # Pattern matched, apply disambiguation
    return apply_context_disambiguation(entry, message, match)


# =============================================================================
# BATCH MATCHING
# =============================================================================


@dataclass
class MatchResult:
    """Result of matching all entries against a message."""

    # All matches (including those that didn't trigger)
    all_results: list[DisambiguationResult] = field(default_factory=list)

    # Only matches that should trigger
    triggered: list[DisambiguationResult] = field(default_factory=list)

    # Categorized by guidance type
    explicit_matches: list[DisambiguationResult] = field(default_factory=list)
    implicit_matches: list[DisambiguationResult] = field(default_factory=list)

    @property
    def has_guidance(self) -> bool:
        """Whether any guidance was detected."""
        return len(self.triggered) > 0

    @property
    def primary_type(self) -> str:
        """Primary guidance type (explicit > implicit > none)."""
        if self.explicit_matches:
            return "explicit"
        if self.implicit_matches:
            return "implicit"
        return "none"

    @property
    def highest_confidence_match(self) -> DisambiguationResult | None:
        """Get the match with highest confidence."""
        if not self.triggered:
            return None
        return max(self.triggered, key=lambda r: r.final_confidence)


def match_all_entries(
    entries: list[LexiconEntry],
    message: str,
) -> MatchResult:
    """
    Match all lexicon entries against a message.

    Args:
        entries: List of lexicon entries to check
        message: The message text

    Returns:
        MatchResult with all matches categorized
    """
    result = MatchResult()

    for entry in entries:
        disambiguation = match_with_disambiguation(entry, message)

        if disambiguation.pattern_matched:
            result.all_results.append(disambiguation)

            if disambiguation.should_trigger:
                result.triggered.append(disambiguation)

                if disambiguation.final_guidance_type == "explicit":
                    result.explicit_matches.append(disambiguation)
                elif disambiguation.final_guidance_type == "implicit":
                    result.implicit_matches.append(disambiguation)

    # Sort by confidence (highest first)
    result.triggered.sort(key=lambda r: -r.final_confidence)
    result.explicit_matches.sort(key=lambda r: -r.final_confidence)
    result.implicit_matches.sort(key=lambda r: -r.final_confidence)

    return result


# =============================================================================
# OBSERVABILITY / LOGGING
# =============================================================================


def format_disambiguation_log(result: DisambiguationResult) -> str:
    """Format a disambiguation result for logging."""
    if not result.pattern_matched:
        return f"[{result.entry.id if result.entry else '?'}] No pattern match"

    entry_id = result.entry.id if result.entry else "?"

    parts = [
        f"[{entry_id}]",
        f"base={result.base_confidence:.2f}",
    ]

    if result.context_adjustment != 0:
        parts.append(f"adj={result.context_adjustment:+.2f}")

    parts.append(f"final={result.final_confidence:.2f}")

    if result.positive_triggered:
        parts.append("+ctx")
    if result.negative_triggered:
        parts.append("-ctx")

    parts.append(f"→ {result.final_guidance_type}")
    parts.append(f"({result.disambiguation_reason})")

    return " ".join(parts)


def log_match_result(result: MatchResult, message: str, level: int = logging.DEBUG):
    """Log a complete match result for observability."""
    preview = message[:50] + "..." if len(message) > 50 else message

    logger.log(
        level,
        f"Guidance detection: {len(result.triggered)} triggered, "
        f"{len(result.explicit_matches)} explicit, "
        f"{len(result.implicit_matches)} implicit | "
        f"message='{preview}'",
    )

    for r in result.all_results:
        logger.debug(f"  {format_disambiguation_log(r)}")


# =============================================================================
# HEDGING PENALTY COMPOUNDING (Issue #524)
# =============================================================================

# Default damping factor for hedging penalty compounding
# Higher values = faster convergence toward -1.0
# Lower values = more conservative compounding
DEFAULT_HEDGING_DAMPING = 0.7

# Suppression threshold: if compounded penalty exceeds this, suppress implicit guidance
# Set to -0.25 so a single strong hedging word (e.g., "maybe" at -0.4 × 0.7 = -0.28) triggers suppression
HEDGING_SUPPRESSION_THRESHOLD = -0.25


def compute_hedging_penalty(
    penalties: list[float],
    damping: float = DEFAULT_HEDGING_DAMPING,
) -> float:
    """
    Compute compounded hedging penalty using damped probabilistic formula.

    This implements a conservative compounding approach where multiple hedging
    signals compound but don't over-penalize. The formula ensures:
    - Single hedging word applies damped penalty
    - Multiple hedging words compound but never exceed -1.0
    - Tunable via damping factor

    Formula:
        effective_penalty = |p| × d
        total = -(1 - (1-|p1|×d) × (1-|p2|×d) × ...)

    Examples with d=0.7:
        Single -0.4 → -(1 - (1 - 0.28)) = -0.28
        Two at -0.4 → -(1 - 0.72 × 0.72) = -0.48
        -0.4 and -0.3 → -(1 - 0.72 × 0.79) = -0.43

    Args:
        penalties: List of penalty values (should be negative, e.g., [-0.4, -0.3])
        damping: Damping factor (0-1). Higher = faster convergence. Default: 0.7

    Returns:
        Compounded penalty as negative float, never exceeds -1.0
    """
    if not penalties:
        return 0.0

    # Compute product of (1 - |p| × d) for each penalty
    product = 1.0
    for p in penalties:
        effective = abs(p) * damping
        # Clamp effective penalty to [0, 1] to prevent math errors
        effective = min(1.0, max(0.0, effective))
        product *= 1.0 - effective

    # Final penalty is -(1 - product)
    return -(1.0 - product)


def should_suppress_implicit_guidance(
    hedging_penalties: list[float],
    threshold: float = HEDGING_SUPPRESSION_THRESHOLD,
    damping: float = DEFAULT_HEDGING_DAMPING,
) -> tuple[bool, float]:
    """
    Determine if implicit guidance should be suppressed based on hedging penalties.

    Args:
        hedging_penalties: List of penalty values from matched hedging patterns
        threshold: Suppression threshold (default: -0.30)
        damping: Damping factor for compounding (default: 0.7)

    Returns:
        Tuple of (should_suppress: bool, compounded_penalty: float)
    """
    if not hedging_penalties:
        return False, 0.0

    compounded = compute_hedging_penalty(hedging_penalties, damping)

    # Suppress if penalty exceeds threshold (both are negative, so use <)
    should_suppress = compounded < threshold

    logger.debug(
        f"Hedging check: penalties={hedging_penalties}, "
        f"compounded={compounded:.3f}, threshold={threshold}, "
        f"suppress={should_suppress}"
    )

    return should_suppress, compounded


# =============================================================================
# UNIT TESTS
# =============================================================================


def run_tests():
    """Run unit tests for disambiguation logic."""
    print("Running disambiguation tests...\n")

    # Test entries
    entries = [
        # Entry without context rule (always triggers)
        LexiconEntry(
            id="test_001",
            pattern=re.compile(r"from\s+now\s+on", re.IGNORECASE),
            category="future_directive",
            guidance_type="explicit",
            confidence=0.95,
        ),
        # Entry with context rule (needs disambiguation)
        # Base 0.55 + positive 0.15 = 0.70 (above 0.60 threshold)
        # Base 0.55 + negative -0.30 = 0.25 (below threshold)
        # Base 0.55 alone = 0.55 (below threshold, won't trigger)
        LexiconEntry(
            id="test_002",
            pattern=re.compile(r"let'?s\s+run", re.IGNORECASE),
            category="imperative_lets",
            guidance_type="explicit",
            confidence=0.55,  # Below threshold, needs positive context
            context_rule=ContextRule(
                positive_pattern=re.compile(
                    r"\b(tests?|evals?|builds?)\b", re.IGNORECASE
                ),
                positive_weight=0.15,
                negative_pattern=re.compile(r"\b(see|away|late)\b", re.IGNORECASE),
                negative_weight=-0.30,
                disambiguation_threshold=0.60,
                fallback_type="none",
            ),
        ),
        # Entry with fallback to implicit
        # Base 0.55 + positive 0.15 = 0.70 (above 0.60 threshold, explicit)
        # Base 0.55 alone = 0.55 (below threshold, falls back to implicit)
        # Base 0.55 + negative -0.35 = 0.20 (way below, still implicit fallback)
        LexiconEntry(
            id="test_003",
            pattern=re.compile(r"can\s+you\s+add", re.IGNORECASE),
            category="question_command",
            guidance_type="explicit",
            confidence=0.55,  # Below threshold, needs context
            context_rule=ContextRule(
                positive_pattern=re.compile(
                    r"\b(please|feature|test)\b", re.IGNORECASE
                ),
                positive_weight=0.15,
                negative_pattern=re.compile(r"\b(explain|why)\b", re.IGNORECASE),
                negative_weight=-0.35,
                disambiguation_threshold=0.60,
                fallback_type="implicit",
            ),
        ),
    ]

    # Test cases
    test_cases = [
        # (message, expected_explicit, expected_implicit, description)
        ("From now on, always run tests first", True, False, "Basic future directive"),
        ("Let's run the tests", True, False, "Let's + positive context"),
        ("Let's run away from here", False, False, "Let's + negative context"),
        ("Let's run", False, False, "Let's without context (below threshold)"),
        ("Can you add a feature please?", True, False, "Question + positive context"),
        ("Can you add something", False, True, "Question falls back to implicit"),
        (
            "Can you explain why this fails?",
            False,
            False,
            "Question + negative context",
        ),
        ("Just a regular message", False, False, "No patterns match"),
    ]

    passed = 0
    failed = 0

    for message, expect_explicit, expect_implicit, description in test_cases:
        result = match_all_entries(entries, message)

        has_explicit = len(result.explicit_matches) > 0
        has_implicit = len(result.implicit_matches) > 0

        if has_explicit == expect_explicit and has_implicit == expect_implicit:
            print(f"✅ PASS: {description}")
            print(f"   Message: '{message}'")
            print(f"   Result: explicit={has_explicit}, implicit={has_implicit}")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Message: '{message}'")
            print(
                f"   Expected: explicit={expect_explicit}, implicit={expect_implicit}"
            )
            print(f"   Got: explicit={has_explicit}, implicit={has_implicit}")
            for r in result.all_results:
                print(f"   {format_disambiguation_log(r)}")
            failed += 1
        print()

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    # Enable debug logging for tests
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    success = run_tests()
    exit(0 if success else 1)
