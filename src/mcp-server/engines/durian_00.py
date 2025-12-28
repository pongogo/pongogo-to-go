"""
DurianRouter00 - Frozen Baseline Routing Engine

This is the frozen baseline version of the durian routing engine, extracted from
commit a2e62f1 (2025-11-22, Issue #130 retrospective). This version was used
during Phase 0B ground truth labeling (497 events).

Routing Algorithm:
1. Parse user message (extract keywords, intent)
2. Extract context (files, directories, git branch, language)
3. Match metadata:
   - Keywords: +10 points (id), +8 points (description), +5 points (tags), +10 points (metadata)
   - Category: +5 points
   - Tags: +3 points
   - Globs (path match): +7 points
   - NLP trigger match: +8 points per overlap
   - Contextual (files, branches): +5 points
4. Apply taxonomy hierarchy
5. Rank by confidence score
6. Select top N instructions

Source: git show a2e62f1:pongogo-knowledge-server/router.py
Frozen: 2025-12-01

References:
    - Phase 0 Semantic Similarity Benchmark (ground truth labeling)
    - Routing Engine Architecture
    - Version Snapshot Infrastructure
"""

import fnmatch
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports when running from engines/
sys.path.insert(0, str(Path(__file__).parent.parent))

from instruction_handler import InstructionHandler
from routing_engine import RoutingEngine, FeatureSpec, register_engine

logger = logging.getLogger(__name__)

# Frozen version identifier - DO NOT CHANGE
DURIAN_VERSION = "durian-00"


@register_engine(DURIAN_VERSION)
class DurianRouter00(RoutingEngine):
    """
    Frozen baseline routing engine (durian-00).

    This is the original rule-based routing implementation used during
    Phase 0B ground truth labeling (based on 497 events). Preserved
    as baseline for A/B comparison with future durian versions.

    Scoring Components:
        - Keywords: +10 per match in id, +8 in description, +5 in tags, +10 in metadata
        - Category: +5 per category match
        - Tags: +3 per tag match
        - Globs: +7 per file pattern match
        - NLP triggers: +8 per intent keyword overlap
        - Contextual: +5 per file/branch context match
    """

    def __init__(self, handler: InstructionHandler):
        """
        Initialize frozen baseline router with instruction handler.

        Args:
            handler: InstructionHandler providing access to knowledge base
        """
        super().__init__(handler)
        # Keep backward-compatible attribute name
        self.instruction_handler = handler
        logger.info(f"DurianRouter00 initialized (version: {self.version})")

    @property
    def version(self) -> str:
        """Return frozen engine version identifier."""
        return DURIAN_VERSION

    @property
    def description(self) -> str:
        """Return human-readable description of routing approach."""
        return "Frozen baseline: Rule-based routing with keyword matching, taxonomy, and context heuristics (Phase 0B)"

    @classmethod
    def get_available_features(cls) -> List[FeatureSpec]:
        """
        Return feature flags available for durian-00.

        durian-00 is a frozen baseline with no configurable features.
        This enables strict reproducibility for A/B comparisons.

        Returns:
            Empty list (no configurable features)
        """
        return []

    def route(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
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
            # Parse message and context
            keywords = self._extract_keywords(message)
            intent = self._extract_intent(message)

            context = context or {}
            files = context.get('files', [])
            directories = context.get('directories', [])
            branch = context.get('branch', '')
            language = context.get('language', '')

            # Score all instructions
            scored_instructions = []
            analysis = {
                'keywords_extracted': keywords,
                'intent_detected': intent,
                'context_used': context,
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
                    language=language
                )

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

            # Sort by score descending
            scored_instructions.sort(key=lambda x: x['routing_score'], reverse=True)

            # Return top N
            top_instructions = scored_instructions[:limit]

            return {
                'instructions': top_instructions,
                'count': len(top_instructions),
                'routing_analysis': analysis
            }

        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return {
                'instructions': [],
                'count': 0,
                'routing_analysis': {'error': str(e)}
            }

    def _extract_keywords(self, message: str) -> List[str]:
        """
        Extract keywords from message.

        Simple implementation: lowercase words, remove common words.
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

        Simple pattern matching.
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
        language: str
    ) -> tuple:
        """
        Score instruction relevance using multiple signals.

        Returns:
            (score, breakdown) where breakdown shows scoring details
        """
        score = 0
        breakdown = {}

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
