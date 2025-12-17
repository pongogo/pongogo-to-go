"""
Instruction Router (durian-00)

Rule-based routing engine implementation using NLP + taxonomy + context + globs.
Part of the RoutingEngine architecture (Spike #188, Task #214).

Routing Algorithm:
1. Parse user message (extract keywords, intent)
2. Extract context (files, directories, git branch, language)
3. Match metadata:
   - Keywords: +10 points
   - Category: +5 points
   - Tags: +3 points
   - Globs (path match): +7 points
   - NLP trigger match: +8 points
4. Apply taxonomy hierarchy
5. Rank by confidence score
6. Select top N instructions

This is Pongogo's differentiator vs all 7 analyzed platforms (0/7 provide semantic routing).

References:
    - Spike #188: Routing Engine Architecture
    - Task #214: Create RoutingEngine Abstract Interface
    - docs/architecture/routing_engine_interface.md
"""

import fnmatch
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

from instruction_handler import InstructionHandler
from routing_engine import RoutingEngine, FeatureSpec, register_engine, set_default_engine

logger = logging.getLogger(__name__)

# Single source of truth for this engine's version
# Used by @register_engine decorator and version property
DURIAN_VERSION = "durian-0.6"

# IMP-003: Simple approval patterns that should suppress routing
# These messages are typically conversational continuations, not queries
APPROVAL_PATTERNS = {
    # Exact matches (case-insensitive)
    'yes', 'ok', 'okay', 'sure', 'go ahead', 'please continue', 'continue',
    'sounds good', 'perfect', 'great', 'excellent', 'good', 'fine', 'nice',
    'thanks', 'thank you', 'ty', 'approved', 'confirmed', 'correct',
    'yes please', 'yes, please', 'please do', 'yes, please do', 'go for it',
    'do it', 'proceed', 'that works', 'that\'s fine', 'that\'s good',
    'looks good', 'lgtm', 'ship it', 'merge it', 'all good', 'no problem',
    'no worries', 'np', 'yep', 'yup', 'yeah', 'uh huh', 'mm hmm',
    'absolutely', 'definitely', 'certainly', 'of course', 'right',
    'exactly', 'precisely', 'agreed', 'understood', 'got it', 'will do',
}

# Word patterns that suggest approval when message is short
APPROVAL_WORDS = {'yes', 'ok', 'okay', 'sure', 'good', 'great', 'fine', 'nice',
                  'perfect', 'excellent', 'thanks', 'approved', 'continue',
                  'proceed', 'agreed', 'correct', 'right', 'yep', 'yeah'}

# IMP-003 refinement: Conservative commencement phrases (table-based, not regex)
# These indicate continuation intent and should NOT suppress routing
# Using exact/prefix phrases to avoid false positives like "please don't", "let's just consider this a failure"
# Evidence: Regex patterns matched 129/497 events but only ~80% were true continuations
# Table grows over time as we discover new legitimate commencement phrases
COMMENCEMENT_PHRASES = [
    # Core continuation phrases - high confidence
    "let's continue",
    "let's proceed",
    "let's resume",
    "let's go ahead",
    "let's get started",
    "let's begin",
    "let's start",
    # Please variants
    "please continue",
    "please proceed",
    "please resume",
    "please go ahead",
    # Yes-prefixed continuations
    "yes, let's continue",
    "yes, let's proceed",
    "yes, let's resume",
    "yes, let's begin",
    "yes, let's start",
    "yes, please continue",
    "yes, please proceed",
    # Go ahead variants
    "go ahead",
    "go ahead and continue",
    "go ahead and proceed",
    # Continue/proceed with
    "continue with",
    "proceed with",
]

# IMP-002: Violation words that should trigger compliance routing
# Evidence: Events 32, 33, 43, 45, 47, 50, 53 from Task #130 missed violations
# Note: Refined to avoid false positives on common technical terms
VIOLATION_WORDS = {
    # Strong user frustration/correction indicators
    'unacceptable', 'wrong', 'incorrect', 'mistake',
    # Frustration indicators (less common in technical discussions)
    'frustrated', 'frustrating', 'annoying', 'annoyed', 'disappointed',
    # Explicit compliance/quality concerns
    'violation', 'violate', 'breach',
    # Quality concerns (clear intent)
    'sloppy', 'careless', 'shortcuts',
}

# Words that are only violations when emphasized (caps, exclamation, etc.)
EMPHASIS_VIOLATION_WORDS = {'no', 'stop', 'bad'}

# Categories to boost when violations detected
VIOLATION_BOOST_CATEGORIES = {'trust_execution', 'safety_prevention'}

# Boost amount for violation detection
VIOLATION_CATEGORY_BOOST = 20

# Foundational instruction score (ensures they appear first when included)
FOUNDATIONAL_SCORE = 1000

# IMP-010: Procedural instruction detection (Task #269)
# When procedural instructions are routed, warn agent to READ before executing
# This addresses the "Instruction Execution from Memory" anti-pattern (Task #200 RCA)
PROCEDURAL_CONTENT_PATTERNS = [
    r'compliance\s*gate',          # COMPLIANCE GATE sections
    r'step\s*\d+[:\s]',            # Step 1:, Step 2:, etc.
    r'phase\s*\d+[:\s]',           # Phase 1:, Phase 2:, etc.
    r'\[\s*\]\s+.*(?:\n.*)*',      # Checklist items
    r'mandatory.*steps?',          # "mandatory steps"
    r'must.*read.*before',         # "must read before"
    r'12-step|13-step|6-step',     # Numbered step processes
]

# Keywords that indicate procedural content when in instruction description/title
PROCEDURAL_KEYWORDS = {
    'checklist', 'step-by-step', 'workflow', 'process', 'procedure',
    'systematic', 'mandatory', 'compliance', '12-step', '13-step',
    'verification', 'validation checklist', 'approval gate',
}

# Minimum relevance score to trigger procedural warning
PROCEDURAL_WARNING_THRESHOLD = 50

# Precompile procedural content patterns
import re as _re_procedural
COMPILED_PROCEDURAL_PATTERNS = [_re_procedural.compile(p, _re_procedural.IGNORECASE) for p in PROCEDURAL_CONTENT_PATTERNS]

# IMP-009: Commencement look-back boost amount
# When commencement detected, boost instructions from previous routing
COMMENCEMENT_LOOKBACK_BOOST = 15

# IMP-007: Co-occurring instruction bundles
# When one instruction is routed, boost co-occurring instructions
# Evidence: Task #204 analysis of 497 ground truth events
# Format: instruction_id -> (co_occurring_id, boost_amount, co_occurrence_rate)
INSTRUCTION_BUNDLES = {
    # Trust execution bundle (55% co-occurrence)
    'trust_execution/development_workflow_essentials': [
        ('trust_execution/trust_based_task_execution', 12, 0.55),
    ],
    'trust_execution/trust_based_task_execution': [
        ('trust_execution/development_workflow_essentials', 12, 0.55),
    ],
    # Batch processing bundle (61% co-occurrence)
    'batch_processing_patterns': [
        ('safety_prevention/systematic_prevention_framework', 10, 0.61),
        ('safety_prevention/validation_first_execution', 8, 0.56),
    ],
    # Docker/container bundle (89% co-occurrence)
    'docker_compose_patterns': [
        ('infrastructure/container_management', 15, 0.89),
    ],
    'infrastructure/container_management': [
        ('docker_compose_patterns', 15, 0.89),
        ('mcp_deployment_architecture', 12, 1.00),  # 100% co-occurrence
    ],
    'mcp_deployment_architecture': [
        ('infrastructure/container_management', 12, 1.00),
    ],
    # Issue closure bundle (62% co-occurrence)
    'github/issue_status_done': [
        ('project_management/issue_closure', 10, 0.62),
    ],
}

# IMP-007: Bundle boost amount
BUNDLE_BOOST_BASE = 10

# IMP-008: Semantic flag patterns for category boosting
# Evidence: Task #204 analysis of 497 ground truth events
# Format: flag_name -> (patterns, boost_categories, boost_amount)
import re as _re  # Needed for precompilation

SEMANTIC_FLAG_PATTERNS = {
    'corrective': {
        'patterns': [
            r'\bno\b', r'\bstop\b', r'\bwrong\b', r'\bincorrect\b', r'\bunacceptable\b',
            r'\bmistake\b', r'\berror\b', r'\bdon\'t\b', r'\bfail\b', r'\bbug\b'
        ],
        'boost_categories': ['trust_execution', 'learning', 'safety_prevention'],
        'boost_amount': 8,
    },
    'directive': {
        'patterns': [
            r'\bplease\s+\w+', r'\bshould\b', r'\bmust\b', r'\bneed\s+to\b', r'\bensure\b',
            r'\balways\b', r'\bnever\b', r'\brequire\b'
        ],
        'boost_categories': ['agentic_workflows', 'safety_prevention', 'project_management'],
        'boost_amount': 5,
    },
    'compliance': {
        'patterns': [
            r'\bfollow\b', r'\badhere\b', r'\bcomplian', r'\bstandard\b',
            r'\bpolicy\b', r'\bprocess\b', r'\bworkflow\b', r'\bguideline\b'
        ],
        'boost_categories': ['safety_prevention', 'agentic_workflows', 'trust_execution'],
        'boost_amount': 8,
    },
    'technical': {
        'patterns': [
            r'\bgit\b', r'\bgithub\b', r'\bdocker\b', r'\bcontainer\b',
            r'\bmcp\b', r'\bserver\b', r'\bapi\b', r'\bdatabase\b', r'\bdb\b'
        ],
        'boost_categories': ['infrastructure', 'github_integration', 'devops'],
        'boost_amount': 6,
    },
    'meta': {
        'patterns': [
            r'\bissue\b', r'\btask\b', r'\bepic\b', r'\bsprint\b', r'\bmilestone\b',
            r'\bproject\b', r'\bstatus\b', r'\bclose\b', r'\bboard\b'
        ],
        'boost_categories': ['github_integration', 'project_management'],
        'boost_amount': 6,
    },
}

# Precompile semantic flag patterns for performance
COMPILED_SEMANTIC_FLAGS = {
    flag_name: {
        'regex': _re.compile('|'.join(config['patterns']), _re.IGNORECASE),
        'boost_categories': config['boost_categories'],
        'boost_amount': config['boost_amount'],
    }
    for flag_name, config in SEMANTIC_FLAG_PATTERNS.items()
}

# IMP-011: Friction patterns from Spike #278 iteration detection
# These are MORE SPECIFIC than semantic_flags "corrective" patterns
# Evidence: 43 friction events (21.5%) in 200-event ground truth
# Types: correction (35), retry (4), rejection (4)
FRICTION_PATTERNS = {
    'correction': [
        # Explicit correction phrases
        r"not\s+good\s+enough",
        r"cutting\s+corners",
        r"against\s+our\s+(goal|broader)",
        r"please\s+remember",
        r"we'?ve\s+been\s+over\s+this",
        r"you\s+(should|need\s+to)\s+undo",
        r"you'?re\s+again",
        r"you\s+had\s+put.*wrong",
        r"that'?s?\s+not\s+(right|correct|what)",
        r"it\s+was\s+meant\s+to\s+be",
        r"you'?re\s+overcomplicating",
        r"don'?t\s+overcomplicate",
        r"i'?m\s+not\s+sure\s+(that\s+)?you\s+did",
        r"you\s+did\s+it\s+(in\s+)?reverse",
        r"you\s+did\s+it\s+wrong",
        r"we\s+already\s+(broke|did|have|completed)",
        # Priority/behavior correction
        r"is\s+not\s+the\s+priority",
        r"focusing\s+on.*is\s+not",
        r"don'?t\s+focus\s+on",
    ],
    'retry': [
        # Context reset indicators
        r"since\s+i'?ve?\s+(exited|re-?entered)",
        r"cleared\s+the\s+context",
        r"context\s+window\s+(reset|cleared)",
        r"let'?s\s+try\s+again",
        r"let'?s\s+retry",
    ],
    'rejection': [
        # Strong rejection markers
        r"^no!+",
        r"\bno!{2,}",
        r"\bunacceptable\b",
        r"completely\s+unacceptable",
        r"this\s+is\s+completely",
        r"(lost|losing)\s+confidence",
        # Failure declaration
        r"consider\s+this\s+a\s+failure",
        r"this\s+is\s+a\s+failure",
        r"this\s+has\s+failed",
        # Reset/revert commands
        r"\brevert\b",
        r"start\s+(again|over)",
        r"delete\s+all",
        r"fully\s+delete",
        r"undo\s+(everything|all)",
    ],
}

# Precompile friction patterns
COMPILED_FRICTION_PATTERNS = {
    friction_type: _re.compile('|'.join(patterns), _re.IGNORECASE)
    for friction_type, patterns in FRICTION_PATTERNS.items()
}

# IMP-011: Friction boost configuration
FRICTION_BOOST_AMOUNT = 20  # Tuned: 20 optimal (8-30 tested)
FRICTION_BOOST_CATEGORIES = ['trust_execution', 'learning', 'safety_prevention', 'development_standards']  # Tuned: 4 optimal

# IMP-012: Mistake type patterns from Spike #284 outcome analysis
# Maps user message patterns to mistake types that require specific preventive instructions
MISTAKE_PATTERNS = {
    'incomplete_implementation': [
        r"not\s+good\s+enough",
        r"thoroughly\s+analyze\s+all",  # More specific
        r"guessing\s+is\s+against",
        r"cutting\s+corners",
        r"goal\s+of\s+completeness",  # Correction context
        r"circumvent.*directive",
        r"abbreviated\s+manner",
        r"lost\s+confidence",
        r"gotten\s+off\s+task",
        r"isn'?t\s+an?\s+accurate\s+reflection",
        r"ongoing\s+problem",
        r"not\s+following\s+the\s+process",
        r"revert.*start\s+again",
        r"(6th|fifth|fourth|third)\s+time.*stop\s+you",  # Repeated correction
    ],
    'premature_action': [
        r"no,?\s+you\s+may\s+not",
        r"please\s+first\s+show",
        r"let'?s\s+determine",
        r"shouldn'?t\s+consider\s+it\s+correct",
        r"did\s+you\s+verify.*first",
        r"before\s+you\s+(do|proceed|continue)",
    ],
    'github_api_misuse': [
        r"don'?t\s+see\s+any\s+changes\s+to\s+the\s+project\s*board",
        r"not\s+in\s+the\s+right\s+place",
        r"serious\s+mistakes.*project\s*board",
        r"should\s+never\s+have\s+been\s+created",
        r"project\s*board.*wrong",
    ],
    'closure_checklist_skip': [
        r"complete\s+this\s+entire\s+checklist",
        r"confirm\s+the\s+status\s+of\s+every",
        r"missing\s+a\s+major\s+procedural\s+gate",
        r"checklist.*not\s+(being\s+)?used",
    ],
    'commencement_checklist_skip': [
        r"did\s+you\s+verify\s+the\s+status\s+of\s+issues?",
        r"check\s+prerequisites?\s+first",
        r"before\s+starting\s+work",
    ],
    'over_engineering': [
        r"overcomplicat(ing|e)",
        r"don'?t\s+overcomplicate",
        r"already\s+(did|done|broke\s+out)",
        r"too\s+complex",
    ],
    'wrong_file_location': [
        r"not\s+the\s+right\s+(place|location|directory)",
        r"should\s+be\s+stored\s+outside",
        r"wrong\s+(place|location|directory)",
        r"moved\s+(them|it)\s+to\s+the\s+correct",
    ],
    'misunderstanding_architecture': [
        r"why\s+are\s+they\s+competing",
        r"became\s+confused",
        r"misunderstand.*architecture",
        r"that'?s\s+not\s+how.*works",
    ],
}

# IMP-012: Map mistake types to preventive instructions (from outcome ground truth)
MISTAKE_INSTRUCTION_MAP = {
    'incomplete_implementation': ['architecture_principles.instructions.md', 'development_workflow.instructions.md'],
    'premature_action': ['issue_closure.instructions.md', 'issue_status_in_progress.instructions.md'],
    'github_api_misuse': ['github_project_status_workflow.instructions.md', 'github_essentials.instructions.md'],
    'closure_checklist_skip': ['issue_closure.instructions.md'],
    'commencement_checklist_skip': ['issue_status_in_progress.instructions.md', 'issue_commencement.instructions.md'],
    'over_engineering': ['architecture_principles.instructions.md'],
    'wrong_file_location': ['documentation_placement.instructions.md', 'repository_organization.instructions.md'],
    'misunderstanding_architecture': ['mcp_deployment_architecture.instructions.md', 'architecture_principles.instructions.md'],
}

# Precompile mistake patterns
COMPILED_MISTAKE_PATTERNS = {
    mistake_type: _re.compile('|'.join(patterns), _re.IGNORECASE)
    for mistake_type, patterns in MISTAKE_PATTERNS.items()
}

# IMP-012: Outcome boost configuration
OUTCOME_BOOST_AMOUNT = 5  # Tuned: 5 optimal (3-20 tested, low values best)

# Default feature configuration (all improvements enabled)
DEFAULT_FEATURES = {
    'violation_detection': True,    # IMP-002: Boost compliance routing on violations
    'approval_suppression': True,   # IMP-003: Suppress routing on simple approvals
    'foundational': True,           # Always-include foundational instructions
    'commencement_lookback': True,  # IMP-009: Look back at previous routing on commencement
    'instruction_bundles': True,    # IMP-007: Boost co-occurring instruction pairs
    'semantic_flags': True,         # IMP-008: Boost categories based on message semantics
    'procedural_warning': True,     # IMP-010: Warn when procedural instructions routed (Task #269)
    'iteration_aware': True,        # IMP-011: Detect friction using Spike #278 patterns
    'friction_boost': True,         # IMP-011: Boost categories when friction detected
    'outcome_aware': True,          # IMP-012: Detect mistake types using Spike #284 patterns
    'outcome_boost': True,          # IMP-012: Boost specific instructions when mistake type detected
}


@register_engine(DURIAN_VERSION)
class RuleBasedRouter(RoutingEngine):
    """
    Rule-based routing engine (durian-0.5-dev).

    Routes user queries to relevant instruction files using keyword matching,
    category/tag filtering, glob patterns, and NLP triggers.

    Scoring Components:
        - Keywords: +10 per match in id, +8 in description, +5 in tags, +10 in metadata
        - Category: +5 per category match
        - Tags: +3 per tag match
        - Globs: +7 per file pattern match
        - NLP triggers: +8 per intent keyword overlap
        - Contextual: +5 per file/branch context match

    Feature Flags (Task #204 Phase 00):
        - violation_detection: Enable IMP-002 violation detection boost
        - approval_suppression: Enable IMP-003 approval message suppression
        - foundational: Enable always-include foundational instructions
        - commencement_lookback: Enable IMP-009 look-back routing on commencement

    This is the baseline routing implementation (durian-00) against which
    future versions (durian-01, durian-02, etc.) will be compared.
    """

    def __init__(self, instruction_handler: InstructionHandler, features: Optional[Dict] = None):
        """
        Initialize rule-based router with instruction handler and feature flags.

        Args:
            instruction_handler: InstructionHandler providing access to knowledge base
            features: Optional dict of feature flags (Task #204 Phase 00):
                - violation_detection: bool (default True) - IMP-002
                - approval_suppression: bool (default True) - IMP-003
                - foundational: bool (default True) - always-include foundational
                - commencement_lookback: bool (default True) - IMP-009
        """
        super().__init__(instruction_handler)
        # Keep backward-compatible attribute name
        self.instruction_handler = instruction_handler

        # Merge provided features with defaults (Task #204 Phase 00)
        self.features = {**DEFAULT_FEATURES, **(features or {})}

        # Log feature configuration
        feature_str = ", ".join(f"{k}={v}" for k, v in self.features.items())
        logger.info(f"RuleBasedRouter initialized (version: {self.version}, features: {feature_str})")

    @property
    def version(self) -> str:
        """Return engine version identifier."""
        # Uses module-level DURIAN_VERSION constant (single source of truth)
        return DURIAN_VERSION

    @property
    def description(self) -> str:
        """Return human-readable description of routing approach."""
        return "Rule-based routing with keyword matching, taxonomy, and context heuristics"

    @classmethod
    def get_available_features(cls) -> List[FeatureSpec]:
        """
        Return feature flags available for durian-0.5-dev.

        Returns:
            List of FeatureSpec objects for this engine's configurable features
        """
        return [
            FeatureSpec(
                name="violation_detection",
                description="IMP-002: Boost compliance routing on frustrated/corrective messages",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="approval_suppression",
                description="IMP-003: Suppress routing for simple approval messages",
                default=True,
                category="routing"
            ),
            FeatureSpec(
                name="foundational",
                description="Always-include foundational instructions (marked foundational: true)",
                default=True,
                category="routing"
            ),
            FeatureSpec(
                name="commencement_lookback",
                description="IMP-009: Boost previous routing results on commencement messages",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="instruction_bundles",
                description="IMP-007: Boost co-occurring instruction pairs based on ground truth analysis",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="semantic_flags",
                description="IMP-008: Boost categories based on message semantic flags (corrective, directive, etc.)",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="procedural_warning",
                description="IMP-010: Warn when procedural instructions are routed (requires Read before execute)",
                default=True,
                category="compliance"
            ),
            FeatureSpec(
                name="iteration_aware",
                description="IMP-011: Detect friction (correction/retry/rejection) using Spike #278 patterns",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="friction_boost",
                description="IMP-011: Boost trust/learning/safety categories when friction detected",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="outcome_aware",
                description="IMP-012: Detect mistake types (incomplete_implementation, premature_action, etc.) using Spike #284 patterns",
                default=True,
                category="scoring"
            ),
            FeatureSpec(
                name="outcome_boost",
                description="IMP-012: Boost specific preventive instructions when mistake type detected",
                default=True,
                category="scoring"
            ),
        ]

    def route(
        self,
        message: str,
        context: Optional[Dict] = None,
        limit: int = 5
    ) -> Dict:
        """
        Route message to relevant instruction files.

        Args:
            message: User message or query
            context: Optional context dictionary with:
                - files: List of file paths
                - directories: List of directory paths
                - branch: Git branch name
                - language: Programming language
            limit: Maximum number of instructions to return

        Returns:
            Dictionary with:
            - instructions: List of matched instructions with scores
            - count: Number of results
            - routing_analysis: Breakdown of routing decision
        """
        try:
            # IMP-003: Early exit for simple approval messages (if enabled)
            # Prevents over-routing on conversational continuations
            # Refinement: Commencement patterns override suppression (work intent detected)
            if self.features.get('approval_suppression', True):
                should_suppress, suppression_reason, commencement_detected = self._is_simple_approval(message)
                if should_suppress:
                    return {
                        'instructions': [],
                        'count': 0,
                        'routing_analysis': {
                            'suppressed': True,
                            'reason': f'IMP-003: {suppression_reason}',
                            'commencement_detected': False,
                            'message_preview': message[:50] if len(message) > 50 else message
                        }
                    }
                elif commencement_detected:
                    # Log that we detected commencement and did NOT suppress
                    logger.info(f"IMP-003: Commencement pattern overrode approval suppression: {message[:50]}")
            else:
                # approval_suppression disabled, so no check performed
                commencement_detected = False

            # Track commencement for analysis (even if approval_suppression disabled)
            commencement_override = commencement_detected if self.features.get('approval_suppression', True) else None

            # Parse message and context
            keywords = self._extract_keywords(message)
            intent = self._extract_intent(message)

            # IMP-002: Detect violations for compliance routing boost (if enabled)
            if self.features.get('violation_detection', True):
                violation_info = self._detect_violations(message)
            else:
                violation_info = {'detected': False, 'signals': [], 'boost_amount': 0}

            # IMP-008: Detect semantic flags for category boosting (if enabled)
            if self.features.get('semantic_flags', True):
                semantic_flags_info = self._detect_semantic_flags(message)
            else:
                semantic_flags_info = {'detected': False, 'flags': [], 'category_boosts': {}}

            # IMP-011: Detect friction using Spike #278 patterns (if enabled)
            if self.features.get('iteration_aware', True):
                friction_info = self._detect_friction(message)
            else:
                friction_info = {'detected': False, 'friction_type': None, 'signals': [], 'category_boosts': {}}

            # IMP-012: Detect mistake types using Spike #284 patterns (if enabled)
            if self.features.get('outcome_aware', True):
                mistake_info = self._detect_mistake_type(message)
            else:
                mistake_info = {'detected': False, 'mistake_type': None, 'signals': [], 'instruction_boosts': []}

            context = context or {}
            files = context.get('files', [])
            directories = context.get('directories', [])
            branch = context.get('branch', '')
            language = context.get('language', '')

            # IMP-009: Commencement look-back for context continuity
            previous_routing_ids = set()
            lookback_info = None
            if commencement_detected and self.features.get('commencement_lookback', True):
                lookback_result = self._get_previous_routing(context)
                if lookback_result and lookback_result.get('instructions'):
                    previous_routing_ids = set(lookback_result['instructions'])
                    lookback_info = {
                        'enabled': True,
                        'found': True,
                        'instruction_count': len(previous_routing_ids),
                        'boost_amount': COMMENCEMENT_LOOKBACK_BOOST
                    }
                    logger.info(f"IMP-009: Will boost {len(previous_routing_ids)} instructions from previous routing")
                else:
                    lookback_info = {'enabled': True, 'found': False}
            elif commencement_detected:
                lookback_info = {'enabled': False, 'reason': 'feature_disabled'}

            # Score all instructions
            scored_instructions = []
            analysis = {
                'keywords_extracted': keywords,
                'intent_detected': intent,
                'context_used': context,
                'features': self.features,  # Task #204 Phase 00: expose active feature flags
                'violation_detection': violation_info if violation_info['detected'] else None,
                'semantic_flags': semantic_flags_info if semantic_flags_info['detected'] else None,  # IMP-008
                'friction_detection': friction_info if friction_info['detected'] else None,  # IMP-011
                'mistake_detection': mistake_info if mistake_info['detected'] else None,  # IMP-012
                'commencement_override': commencement_override,  # IMP-003 refinement tracking
                'commencement_lookback': lookback_info,  # IMP-009 look-back tracking
                'scoring_breakdown': []
            }

            for instruction in self.instruction_handler.instructions.values():
                score, score_breakdown = self._score_instruction(
                    instruction=instruction,
                    message=message,
                    keywords=keywords,
                    intent=intent,
                    files=files,
                    directories=directories,
                    branch=branch,
                    language=language,
                    violation_info=violation_info,  # IMP-002
                    semantic_flags_info=semantic_flags_info  # IMP-008
                )

                # IMP-009: Apply commencement look-back boost
                # Normalize instruction ID for comparison (handle category/name and name.instructions formats)
                if previous_routing_ids:
                    inst_id_normalized = self._normalize_instruction_id(instruction)
                    if inst_id_normalized in previous_routing_ids:
                        score += COMMENCEMENT_LOOKBACK_BOOST
                        score_breakdown['commencement_lookback'] = COMMENCEMENT_LOOKBACK_BOOST
                        logger.debug(f"IMP-009: Boosted {instruction.id} (normalized: {inst_id_normalized}) by {COMMENCEMENT_LOOKBACK_BOOST}")

                # IMP-011: Apply friction boost when friction detected and friction_boost enabled
                if friction_info['detected'] and self.features.get('friction_boost', True):
                    for inst_category in instruction.categories:
                        if inst_category in FRICTION_BOOST_CATEGORIES:
                            score += FRICTION_BOOST_AMOUNT
                            score_breakdown['friction_boost'] = {
                                'category': inst_category,
                                'boost': FRICTION_BOOST_AMOUNT,
                                'friction_type': friction_info.get('friction_type')
                            }
                            logger.debug(f"IMP-011: Friction boost for {instruction.id} (category: {inst_category}) by {FRICTION_BOOST_AMOUNT}")
                            break  # Only apply once per instruction

                # IMP-012: Apply outcome boost when mistake type detected and outcome_boost enabled
                if mistake_info['detected'] and self.features.get('outcome_boost', True):
                    # Check if this instruction is in the list of preventive instructions
                    inst_filename = instruction.file_path.name if hasattr(instruction, 'file_path') else ''
                    for preventive_inst in mistake_info.get('instruction_boosts', []):
                        if preventive_inst in inst_filename or inst_filename in preventive_inst:
                            score += OUTCOME_BOOST_AMOUNT
                            score_breakdown['outcome_boost'] = {
                                'instruction': preventive_inst,
                                'boost': OUTCOME_BOOST_AMOUNT,
                                'mistake_type': mistake_info.get('mistake_type')
                            }
                            logger.debug(f"IMP-012: Outcome boost for {instruction.id} (preventive: {preventive_inst}) by {OUTCOME_BOOST_AMOUNT}")
                            break  # Only apply once per instruction

                if score > 0:
                    result = instruction.to_dict()
                    result['routing_score'] = score
                    result['score_breakdown'] = score_breakdown
                    scored_instructions.append(result)

                    analysis['scoring_breakdown'].append({
                        'instruction_id': instruction.id,
                        'score': score,
                        'breakdown': score_breakdown
                    })

            # IMP-007: Apply bundle boost for co-occurring instructions
            bundle_boost_info = None
            if self.features.get('instruction_bundles', True):
                bundle_boost_info = self._apply_bundle_boost(scored_instructions)
                if bundle_boost_info.get('applied'):
                    analysis['bundle_boost'] = bundle_boost_info
                    logger.debug(f"IMP-007: Applied bundle boosts: {bundle_boost_info}")

            # Sort by score descending
            scored_instructions.sort(key=lambda x: x['routing_score'], reverse=True)

            # Get foundational instructions (if enabled)
            if self.features.get('foundational', True):
                foundational = self._get_foundational_instructions()
                foundational_ids = {inst.get('id') for inst in foundational}

                # Get top N query-specific (excluding foundational to avoid duplicates)
                query_specific = [
                    inst for inst in scored_instructions[:limit]
                    if inst.get('id') not in foundational_ids
                ]

                # Combine: foundational first, then query-specific
                # Foundational don't count against limit
                combined = foundational + query_specific

                # Update analysis with foundational info
                analysis['foundational_count'] = len(foundational)
                analysis['foundational_ids'] = list(foundational_ids)
                analysis['query_specific_count'] = len(query_specific)
            else:
                # Foundational disabled - just return top N query-specific
                combined = scored_instructions[:limit]
                analysis['foundational_count'] = 0
                analysis['foundational_ids'] = []
                analysis['foundational_disabled'] = True
                analysis['query_specific_count'] = len(combined)

            # IMP-010: Check for procedural instructions and generate warning (if enabled)
            procedural_warning = None
            if self.features.get('procedural_warning', True):
                procedural_instructions = []
                for inst in combined:
                    # Get the original instruction object to check content
                    inst_id = inst.get('id', '')
                    original_inst = self.instruction_handler.instructions.get(inst_id)
                    if original_inst:
                        procedural_info = self._is_procedural_instruction(original_inst)
                        if procedural_info['is_procedural']:
                            # Check if this instruction has high enough relevance
                            score = inst.get('routing_score', 0)
                            if score >= PROCEDURAL_WARNING_THRESHOLD or inst.get('score_breakdown', {}).get('foundational'):
                                procedural_instructions.append({
                                    'id': inst_id,
                                    'score': score,
                                    'detection_method': procedural_info['detection_method'],
                                    'referenced_doc': procedural_info['referenced_doc']
                                })

                if procedural_instructions:
                    # Generate warning message
                    warning_parts = ["⚠️ PROCEDURAL INSTRUCTION(S) ROUTED - READ BEFORE EXECUTING:"]
                    for proc_inst in procedural_instructions:
                        if proc_inst['referenced_doc']:
                            warning_parts.append(f"  • {proc_inst['id']}: Read `{proc_inst['referenced_doc']}` first")
                        else:
                            warning_parts.append(f"  • {proc_inst['id']}: Read instruction file before executing")

                    procedural_warning = {
                        'warning': '\n'.join(warning_parts),
                        'instructions': procedural_instructions,
                        'count': len(procedural_instructions),
                        'enforcement': 'Read tool call required before action (Task #200 RCA)'
                    }
                    analysis['procedural_warning'] = procedural_warning
                    logger.info(f"IMP-010: Procedural warning generated for {len(procedural_instructions)} instruction(s)")

            return {
                'instructions': combined,
                'count': len(combined),
                'routing_analysis': analysis,
                'procedural_warning': procedural_warning
            }

        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return {
                'instructions': [],
                'count': 0,
                'routing_analysis': {'error': str(e)}
            }

    def _detect_violations(self, message: str) -> Dict[str, Any]:
        """
        Detect violation signals in message that should boost compliance routing.

        IMP-002: Violation detection to route frustrated/corrective messages to compliance files.
        Evidence: Events 32, 33, 43, 45, 47, 50, 53 missed violations in Task #130 analysis.

        Detection signals:
        1. Violation words (NO, stop, wrong, etc.)
        2. Exclamation mark density (frustration indicator)
        3. ALL CAPS words (emphasis/frustration)

        Args:
            message: User message to analyze

        Returns:
            Dictionary with:
            - detected: True if violations found
            - signals: List of detected signals
            - boost_amount: Recommended score boost for compliance categories
        """
        signals = []
        message_lower = message.lower()

        # Check 1: Strong violation words (always trigger)
        words = re.findall(r'\b\w+\b', message_lower)
        violation_matches = set(words) & VIOLATION_WORDS
        if violation_matches:
            signals.append(f"violation_words:{','.join(violation_matches)}")

        # Check 2: Emphasis-only violation words (need caps, exclamation, or sentence-start)
        for word in EMPHASIS_VIOLATION_WORDS:
            # Check for capitalized version (e.g., "NO", "STOP")
            if re.search(rf'\b{word.upper()}\b', message):
                signals.append(f"emphasized_{word.upper()}")
            # Check for word with exclamation (e.g., "no!", "stop!")
            elif re.search(rf'\b{word}\s*!', message_lower):
                signals.append(f"exclaimed_{word}")
            # Check for sentence-start negation (e.g., "No, that's wrong")
            elif re.search(rf'(?:^|[.!?]\s*){word}[,\s]', message_lower):
                signals.append(f"sentence_start_{word}")

        # Check 3: High exclamation density (3+ indicates strong emotion)
        exclaim_count = message.count('!')
        if exclaim_count >= 3:
            signals.append(f"exclamation_density:{exclaim_count}")

        # Check 4: ALL CAPS words (frustration indicator, 2+ words needed)
        caps_words = [w for w in message.split() if w.isupper() and len(w) > 2 and w.isalpha()]
        if len(caps_words) >= 2:
            signals.append(f"caps_emphasis:{','.join(caps_words[:3])}")

        # Calculate boost
        boost_amount = 0
        if signals:
            boost_amount = VIOLATION_CATEGORY_BOOST * len(signals)
            logger.debug(f"IMP-002: Violation detected - signals: {signals}, boost: {boost_amount}")

        return {
            'detected': len(signals) > 0,
            'signals': signals,
            'boost_amount': boost_amount
        }

    def _is_simple_approval(self, message: str) -> tuple:
        """
        Detect if message is a simple approval that should suppress routing.

        IMP-003: Over-routing on simple approvals wastes context.
        Evidence: 89 events (17.9%) were over-routed in Task #130 analysis.

        IMP-003 Refinement: Commencement patterns override approval suppression.
        Evidence: Events 351, 402, 445, 446, 457, 495 were false positives.
        Messages like "yes, let's continue" indicate work intent, not simple approval.

        Suppression criteria:
        1. NOT a commencement pattern (overrides all below)
        2. Exact match with known approval patterns
        3. Short message (≤5 words) containing approval words
        4. Message ≤ 3 words with positive sentiment

        Args:
            message: User message to evaluate

        Returns:
            Tuple of (should_suppress: bool, reason: str, commencement_detected: bool)
        """
        # Normalize message
        message_clean = message.strip().lower()
        # Remove trailing punctuation for matching
        message_normalized = re.sub(r'[.!?,]+$', '', message_clean)

        # Check 0: Commencement phrases OVERRIDE approval suppression
        # These indicate work intent despite approval-like prefix
        # Using conservative phrase table instead of broad regex patterns
        for phrase in COMMENCEMENT_PHRASES:
            if message_clean.startswith(phrase) or f" {phrase}" in message_clean:
                logger.debug(f"IMP-003: Commencement phrase detected, NOT suppressing: {message_clean}")
                return (False, 'commencement_phrase_detected', True)

        # Check 1: Exact match with approval patterns
        if message_normalized in APPROVAL_PATTERNS:
            logger.debug(f"IMP-003: Suppressing routing for approval pattern: {message_clean}")
            return (True, 'exact_approval_match', False)

        # Check 2: Very short message (≤3 words) - likely approval
        words = message_clean.split()
        if len(words) <= 3:
            # Check if any word is an approval word
            if any(word.rstrip('.,!?') in APPROVAL_WORDS for word in words):
                logger.debug(f"IMP-003: Suppressing routing for short approval: {message_clean}")
                return (True, 'short_approval_message', False)

        # Check 3: Short message (≤5 words) dominated by approval words
        if len(words) <= 5:
            approval_count = sum(1 for word in words if word.rstrip('.,!?') in APPROVAL_WORDS)
            if approval_count >= len(words) / 2:  # Majority are approval words
                logger.debug(f"IMP-003: Suppressing routing for approval-dominated message: {message_clean}")
                return (True, 'approval_dominated_message', False)

        return (False, 'not_approval', False)

    def _get_foundational_instructions(self) -> List[Dict]:
        """
        Return instructions marked as foundational (always-included).

        Foundational instructions provide core context for all agent work.
        They are included with every routing result (except IMP-003 suppressions).

        Foundational status is determined by frontmatter:
            foundational: true

        Returns:
            List of instruction dictionaries marked as foundational
        """
        foundational = []
        for instruction in self.instruction_handler.instructions.values():
            # Check for foundational flag in metadata
            metadata = instruction.metadata or {}
            if metadata.get('foundational', False):
                result = instruction.to_dict()
                result['routing_score'] = FOUNDATIONAL_SCORE
                result['score_breakdown'] = {'foundational': True}
                foundational.append(result)
                logger.debug(f"Foundational instruction: {instruction.id}")

        return foundational

    def _get_previous_routing(self, context: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get previous routing result for commencement look-back.

        IMP-009: When commencement detected, boost instructions from previous routing.
        This provides context continuity for messages like "yes, let's continue".

        Lookup order:
        1. Check context['previous_routing'] if provided (explicit)
        2. Query observability DB for last routing event (implicit)

        Args:
            context: Optional context dict that may contain 'previous_routing'

        Returns:
            Dict with 'instructions' list, or None if not available
        """
        # Option 1: Explicit previous routing in context
        if context and 'previous_routing' in context:
            logger.debug("IMP-009: Using explicit previous_routing from context")
            return context['previous_routing']

        # Option 2: Query observability DB
        # Look for .observability_db relative to knowledge base or current working directory
        db_paths = [
            Path.cwd() / '.observability_db' / 'observability_db-production' / 'routing_log-production.db',
            Path.cwd().parent / '.observability_db' / 'observability_db-production' / 'routing_log-production.db',
        ]

        for db_path in db_paths:
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()

                    # Get most recent routing event (excluding current - look for previous)
                    cursor.execute("""
                        SELECT instruction_ids, instruction_scores
                        FROM routing_events
                        WHERE instruction_count > 0
                        ORDER BY timestamp DESC
                        LIMIT 1 OFFSET 1
                    """)
                    row = cursor.fetchone()
                    conn.close()

                    if row and row[0]:
                        instruction_ids = row[0].split(',') if row[0] else []
                        logger.debug(f"IMP-009: Found previous routing with {len(instruction_ids)} instructions")
                        return {'instructions': instruction_ids}

                except Exception as e:
                    logger.warning(f"IMP-009: Error querying observability DB: {e}")
                    continue

        logger.debug("IMP-009: No previous routing found")
        return None

    def _normalize_instruction_id(self, instruction) -> str:
        """
        Normalize instruction ID to category/name format for comparison.

        IMP-009: Ensures consistent ID format between router output and ground truth.

        The eval harness uses category/name format (e.g., trust_execution/trust_based_task_execution).
        Instruction handler uses name.instructions format (e.g., trust_based_task_execution.instructions).

        This method normalizes to category/name format for consistent matching.

        Args:
            instruction: InstructionFile object

        Returns:
            Normalized ID in category/name format
        """
        # Get base ID without .instructions suffix
        inst_id = instruction.id
        if inst_id.endswith('.instructions'):
            inst_id = inst_id[:-len('.instructions')]

        # Get category from instruction metadata
        categories = instruction.categories or []
        if categories:
            return f"{categories[0]}/{inst_id}"
        else:
            return inst_id

    def _extract_keywords(self, message: str) -> List[str]:
        """
        Extract keywords from message.

        Simple implementation: lowercase words, remove common words.
        Future: Use NLP library (spaCy, NLTK) for better extraction.
        """
        # Convert to lowercase
        message_lower = message.lower()

        # Remove punctuation
        message_clean = re.sub(r'[^\w\s]', ' ', message_lower)

        # Split into words
        words = message_clean.split()

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                      'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}

        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _extract_intent(self, message: str) -> str:
        """
        Extract intent from message.

        Simple pattern matching. Future: Use intent classification model.
        """
        message_lower = message.lower()

        # Common intent patterns
        if any(word in message_lower for word in ['how do i', 'how to', 'how can']):
            return 'how-to'
        elif any(word in message_lower for word in ['what is', 'what are', 'explain']):
            return 'explanation'
        elif any(word in message_lower for word in ['create', 'add', 'make', 'build']):
            return 'creation'
        elif any(word in message_lower for word in ['fix', 'debug', 'error', 'issue', 'problem']):
            return 'troubleshooting'
        elif any(word in message_lower for word in ['test', 'validate', 'check']):
            return 'validation'
        elif any(word in message_lower for word in ['document', 'write docs', 'readme']):
            return 'documentation'

        return 'general'

    def _score_instruction(
        self,
        instruction,
        message: str,
        keywords: List[str],
        intent: str,
        files: List[str],
        directories: List[str],
        branch: str,
        language: str,
        violation_info: Optional[Dict] = None,  # IMP-002
        semantic_flags_info: Optional[Dict] = None  # IMP-008
    ) -> tuple[int, Dict]:
        """
        Score instruction relevance using multiple signals.

        Returns:
            (score, breakdown) where breakdown shows scoring details
        """
        score = 0
        breakdown = {}

        # IMP-002: Apply violation boost to compliance categories
        if violation_info and violation_info.get('detected'):
            for category in instruction.categories:
                if category in VIOLATION_BOOST_CATEGORIES:
                    score += violation_info['boost_amount']
                    breakdown['violation_boost'] = {
                        'category': category,
                        'boost': violation_info['boost_amount'],
                        'signals': violation_info['signals']
                    }
                    break  # Only apply once per instruction

        # IMP-008: Apply semantic flag boost to matching categories
        if semantic_flags_info and semantic_flags_info.get('detected'):
            category_boosts = semantic_flags_info.get('category_boosts', {})
            for category in instruction.categories:
                if category in category_boosts:
                    boost = category_boosts[category]
                    score += boost
                    if 'semantic_flag_boost' not in breakdown:
                        breakdown['semantic_flag_boost'] = []
                    breakdown['semantic_flag_boost'].append({
                        'category': category,
                        'boost': boost,
                        'flags': semantic_flags_info.get('flags', [])
                    })

        # 1. Keyword matching (+10 per keyword match)
        keyword_matches = []
        for keyword in keywords:
            # Check in id
            if keyword in instruction.id.lower():
                score += 10
                keyword_matches.append(f"id:{keyword}")

            # Check in description
            if keyword in instruction.description.lower():
                score += 8
                keyword_matches.append(f"description:{keyword}")

            # Check in tags
            for tag in instruction.tags:
                if keyword in tag.lower():
                    score += 5
                    keyword_matches.append(f"tag:{tag}")

            # Check in metadata keywords
            routing = instruction.routing or {}
            triggers = routing.get('triggers', {})
            meta_keywords = triggers.get('keywords', [])
            for meta_keyword in meta_keywords:
                if keyword in meta_keyword.lower():
                    score += 10
                    keyword_matches.append(f"metadata_keyword:{meta_keyword}")

        if keyword_matches:
            breakdown['keyword_matches'] = keyword_matches

        # 2. Category matching (+5 per category)
        category_matches = []
        for category in instruction.categories:
            # Direct keyword match
            if any(keyword in category.lower() for keyword in keywords):
                score += 5
                category_matches.append(category)

        if category_matches:
            breakdown['category_matches'] = category_matches

        # 3. NLP trigger matching (+8)
        routing = instruction.routing or {}
        triggers = routing.get('triggers', {})
        nlp_trigger = triggers.get('nlp', '')
        if nlp_trigger:
            # Check if message matches NLP trigger description
            nlp_keywords = self._extract_keywords(nlp_trigger)
            overlap = set(keywords) & set(nlp_keywords)
            if overlap:
                score += 8 * len(overlap)
                breakdown['nlp_trigger_match'] = list(overlap)

        # 4. Glob/path matching (+7 per file match)
        glob_matches = []
        apply_to = routing.get('applyTo', {})
        globs = apply_to.get('globs', [])

        for file_path in files:
            for glob_pattern in globs:
                if fnmatch.fnmatch(file_path, glob_pattern):
                    score += 7
                    glob_matches.append(f"{file_path} matches {glob_pattern}")

        if glob_matches:
            breakdown['glob_matches'] = glob_matches

        # 5. Contextual matching (files, branches) (+5)
        contextual_matches = []
        contextual = routing.get('contextual', {})

        # File context
        file_patterns = contextual.get('files', [])
        for file_path in files:
            for pattern in file_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    score += 5
                    contextual_matches.append(f"file_context:{file_path}")

        # Branch context
        branch_patterns = contextual.get('branches', [])
        for pattern in branch_patterns:
            if fnmatch.fnmatch(branch, pattern):
                score += 5
                contextual_matches.append(f"branch_context:{branch}")

        if contextual_matches:
            breakdown['contextual_matches'] = contextual_matches

        # 6. Tag matching (+3 per tag)
        tag_matches = []
        for tag in instruction.tags:
            if any(keyword in tag.lower() for keyword in keywords):
                score += 3
                tag_matches.append(tag)

        if tag_matches:
            breakdown['tag_matches'] = tag_matches

        breakdown['total_score'] = score
        return score, breakdown

    def _detect_semantic_flags(self, message: str) -> Dict[str, Any]:
        """
        Detect semantic flags in message for category boosting.

        IMP-008: Semantic flag integration to boost categories based on message content.
        Evidence: Task #204 analysis of 497 ground truth events.

        Semantic flags:
        - corrective: User correction signals → boost trust_execution, learning
        - directive: Instructional language → boost agentic_workflows, safety_prevention
        - compliance: Policy/process mentions → boost safety_prevention, agentic_workflows
        - technical: Technical terms (docker, git, etc.) → boost infrastructure, github_integration
        - meta: Project management terms → boost github_integration, project_management

        Args:
            message: User message to analyze

        Returns:
            Dictionary with:
            - detected: True if any flags found
            - flags: List of detected flag names
            - category_boosts: Dict of category -> boost amount
        """
        flags = []
        category_boosts = {}

        for flag_name, config in COMPILED_SEMANTIC_FLAGS.items():
            if config['regex'].search(message):
                flags.append(flag_name)
                # Accumulate boosts per category
                for category in config['boost_categories']:
                    if category not in category_boosts:
                        category_boosts[category] = 0
                    category_boosts[category] += config['boost_amount']

        if flags:
            logger.debug(f"IMP-008: Semantic flags detected: {flags}, category boosts: {category_boosts}")

        return {
            'detected': len(flags) > 0,
            'flags': flags,
            'category_boosts': category_boosts
        }

    def _detect_friction(self, message: str) -> Dict[str, Any]:
        """
        Detect friction (correction/retry/rejection) using Spike #278 patterns.

        IMP-011: Enhanced friction detection for routing boost.
        Evidence: Spike #278 identified 43 friction events (21.5%) in 200-event ground truth.

        Friction types (all indicate user frustration/correction):
        - correction: Pointing out errors ("that's not right", "you did it wrong")
        - retry: Resending after failure ("let's try again", "context reset")
        - rejection: Full rejection ("unacceptable", "start over", "revert")

        Args:
            message: User message to analyze

        Returns:
            Dictionary with:
            - detected: True if friction detected
            - friction_type: Type of friction (correction/retry/rejection) or None
            - signals: List of matched patterns
            - category_boosts: Dict of category -> boost amount (for friction_boost feature)
        """
        signals = []
        friction_type = None

        # Check each friction type in priority order (rejection > retry > correction)
        for ftype in ['rejection', 'retry', 'correction']:
            pattern = COMPILED_FRICTION_PATTERNS[ftype]
            match = pattern.search(message)
            if match:
                signals.append(f"{ftype}:{match.group()[:20]}")
                if friction_type is None:
                    friction_type = ftype  # First match wins (priority order)

        if signals:
            logger.debug(f"IMP-011: Friction detected: type={friction_type}, signals={signals}")

        # Build category boosts (only used if friction_boost feature enabled)
        category_boosts = {}
        if friction_type:
            for category in FRICTION_BOOST_CATEGORIES:
                category_boosts[category] = FRICTION_BOOST_AMOUNT

        return {
            'detected': len(signals) > 0,
            'friction_type': friction_type,
            'signals': signals,
            'category_boosts': category_boosts
        }

    def _detect_mistake_type(self, message: str) -> Dict[str, Any]:
        """
        Detect mistake types using Spike #284 outcome patterns.

        IMP-012: Mistake type detection for targeted instruction boosting.
        Evidence: Spike #284 identified mistake types and their preventive instructions.

        Mistake types (indicate specific errors that have known preventive instructions):
        - incomplete_implementation: Cutting corners, not thorough enough
        - premature_action: Acting without proper verification
        - github_api_misuse: Project board or GitHub API errors
        - closure_checklist_skip: Missing closure verification steps
        - commencement_checklist_skip: Missing startup verification steps
        - over_engineering: Making things too complex
        - wrong_file_location: Placing files in wrong directories
        - misunderstanding_architecture: Architectural confusion

        Args:
            message: User message to analyze

        Returns:
            Dictionary with:
            - detected: True if mistake type detected
            - mistake_type: Type of mistake or None
            - signals: List of matched patterns
            - instruction_boosts: List of instruction filenames to boost
        """
        signals = []
        mistake_type = None
        instruction_boosts = []

        # Check each mistake type
        for mtype, pattern in COMPILED_MISTAKE_PATTERNS.items():
            match = pattern.search(message)
            if match:
                signals.append(f"{mtype}:{match.group()[:30]}")
                if mistake_type is None:
                    mistake_type = mtype  # First match wins
                    # Get preventive instructions for this mistake type
                    instruction_boosts = MISTAKE_INSTRUCTION_MAP.get(mtype, [])

        if signals:
            logger.debug(f"IMP-012: Mistake type detected: type={mistake_type}, signals={signals}, boosts={instruction_boosts}")

        return {
            'detected': len(signals) > 0,
            'mistake_type': mistake_type,
            'signals': signals,
            'instruction_boosts': instruction_boosts
        }

    def _is_procedural_instruction(self, instruction) -> Dict[str, Any]:
        """
        Detect if an instruction is procedural (requires Read before execute).

        IMP-010: Procedural instruction detection (Task #269)
        When procedural instructions are routed, warn agent to READ before executing.
        This addresses the "Instruction Execution from Memory" anti-pattern (Task #200 RCA).

        Detection methods:
        1. Metadata field: procedural: true in frontmatter
        2. Content patterns: COMPLIANCE GATE, Step N:, Phase N:, checklists
        3. Keywords in description: checklist, step-by-step, workflow, etc.

        Args:
            instruction: InstructionFile object to analyze

        Returns:
            Dictionary with:
            - is_procedural: True if procedural instruction detected
            - detection_method: How it was detected (metadata, content, keywords)
            - referenced_doc: Document that must be read (if referenced in instruction)
        """
        metadata = instruction.metadata or {}

        # Method 1: Explicit metadata flag
        if metadata.get('procedural', False):
            return {
                'is_procedural': True,
                'detection_method': 'metadata_flag',
                'referenced_doc': None
            }

        # Method 2: Check for COMPLIANCE GATE in content
        content = instruction.content or ''
        content_lower = content.lower()

        # Check for compliance gate (most important signal)
        if 'compliance gate' in content_lower or 'compliance_gate' in content_lower:
            # Try to extract referenced document
            referenced_doc = None
            # Pattern: Read `docs/templates/issue_closure_checklist.md`
            doc_match = re.search(r'[Rr]ead\s+[`"\']?([^`"\']+\.md)[`"\']?', content)
            if doc_match:
                referenced_doc = doc_match.group(1)

            return {
                'is_procedural': True,
                'detection_method': 'compliance_gate',
                'referenced_doc': referenced_doc
            }

        # Method 3: Content pattern matching (step-by-step, checklists)
        for pattern in COMPILED_PROCEDURAL_PATTERNS:
            if pattern.search(content):
                return {
                    'is_procedural': True,
                    'detection_method': 'content_pattern',
                    'referenced_doc': None
                }

        # Method 4: Keywords in description
        description_lower = instruction.description.lower()
        for keyword in PROCEDURAL_KEYWORDS:
            if keyword in description_lower:
                return {
                    'is_procedural': True,
                    'detection_method': f'keyword:{keyword}',
                    'referenced_doc': None
                }

        return {
            'is_procedural': False,
            'detection_method': None,
            'referenced_doc': None
        }

    def _apply_bundle_boost(self, scored_instructions: List[Dict]) -> Dict[str, Any]:
        """
        Apply bundle boost for co-occurring instruction pairs.

        IMP-007: When one instruction from a bundle is present in results,
        boost its co-occurring pair if also present.

        Evidence: Task #204 analysis of 497 ground truth events found
        strong co-occurrence patterns (55-100%) in instruction pairs.

        Args:
            scored_instructions: List of scored instruction dictionaries

        Returns:
            Dictionary with:
            - applied: True if any boosts applied
            - boosts: List of boost details
        """
        boosts_applied = []

        # Get set of instruction IDs currently in results
        instruction_ids = set()
        for inst in scored_instructions:
            # Normalize instruction ID to category/name format
            inst_id = inst.get('id', '')
            categories = inst.get('categories', [])
            if categories and '/' not in inst_id:
                normalized_id = f"{categories[0]}/{inst_id}"
            else:
                normalized_id = inst_id
            instruction_ids.add(normalized_id)
            # Also add without .instructions suffix if present
            if normalized_id.endswith('.instructions'):
                instruction_ids.add(normalized_id[:-len('.instructions')])

        # Check each instruction against bundle definitions
        for inst in scored_instructions:
            inst_id = inst.get('id', '')
            categories = inst.get('categories', [])

            # Try multiple ID formats
            ids_to_check = [inst_id]
            if categories:
                ids_to_check.append(f"{categories[0]}/{inst_id}")
            if inst_id.endswith('.instructions'):
                ids_to_check.append(inst_id[:-len('.instructions')])
                if categories:
                    ids_to_check.append(f"{categories[0]}/{inst_id[:-len('.instructions')]}")

            for id_format in ids_to_check:
                if id_format in INSTRUCTION_BUNDLES:
                    bundle_partners = INSTRUCTION_BUNDLES[id_format]
                    for partner_id, boost_amount, co_occurrence_rate in bundle_partners:
                        # Check if partner is in results
                        if partner_id in instruction_ids:
                            # Find and boost the partner instruction
                            for partner_inst in scored_instructions:
                                p_id = partner_inst.get('id', '')
                                p_categories = partner_inst.get('categories', [])
                                p_normalized = f"{p_categories[0]}/{p_id}" if p_categories else p_id

                                if partner_id == p_id or partner_id == p_normalized:
                                    partner_inst['routing_score'] += boost_amount
                                    if 'score_breakdown' not in partner_inst:
                                        partner_inst['score_breakdown'] = {}
                                    partner_inst['score_breakdown']['bundle_boost'] = {
                                        'from': id_format,
                                        'boost': boost_amount,
                                        'co_occurrence_rate': co_occurrence_rate
                                    }
                                    boosts_applied.append({
                                        'trigger': id_format,
                                        'boosted': partner_id,
                                        'amount': boost_amount
                                    })
                                    break
                    break  # Found matching ID format, no need to check others

        return {
            'applied': len(boosts_applied) > 0,
            'boosts': boosts_applied,
            'total_boosts': len(boosts_applied)
        }


# Backward compatibility alias
# Existing code using InstructionRouter will continue to work
InstructionRouter = RuleBasedRouter

# Set this engine as the default for the factory
# This is the single place that determines the default engine
set_default_engine(DURIAN_VERSION)
