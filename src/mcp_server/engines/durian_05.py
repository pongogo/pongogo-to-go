"""
DurianRouter05 - Frozen Stable Routing Engine (durian-0.5)

This is the frozen stable version of the durian routing engine, extracted from
commit 1a0933b (2025-12-04, "Promote durian-0.5-dev to durian-0.5").

This version includes all  through  features but NOT
(procedural warnings). Preserved for A/B comparison and rollback.

Features (all enabled by default):
- Violation detection (boost compliance routing on frustration)
- Approval suppression (skip routing for "yes", "ok", etc.)
- Instruction bundles (boost co-occurring pairs)
- Semantic flags (boost categories based on message content)
- Commencement lookback (boost previous routing on continuation)
- Foundational: Always-include foundational instructions

Source: git show 1a0933b:pongogo-knowledge-server/router.py
Frozen: 2025-12-10 (versioning update)

References:
    - Quick Wins Implementation
    - Routing Engine Architecture
    - RoutingEngine Abstract Interface
"""

import fnmatch
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports when running from engines/
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.instruction_handler import InstructionHandler
from mcp_server.routing_engine import FeatureSpec, RoutingEngine, register_engine

logger = logging.getLogger(__name__)

# Frozen version identifier - DO NOT CHANGE
DURIAN_VERSION = "durian-0.5"

# Simple approval patterns that should suppress routing
APPROVAL_PATTERNS = {
    "yes",
    "ok",
    "okay",
    "sure",
    "go ahead",
    "please continue",
    "continue",
    "sounds good",
    "perfect",
    "great",
    "excellent",
    "good",
    "fine",
    "nice",
    "thanks",
    "thank you",
    "ty",
    "approved",
    "confirmed",
    "correct",
    "yes please",
    "yes, please",
    "please do",
    "yes, please do",
    "go for it",
    "do it",
    "proceed",
    "that works",
    "that's fine",
    "that's good",
    "looks good",
    "lgtm",
    "ship it",
    "merge it",
    "all good",
    "no problem",
    "no worries",
    "np",
    "yep",
    "yup",
    "yeah",
    "uh huh",
    "mm hmm",
    "absolutely",
    "definitely",
    "certainly",
    "of course",
    "right",
    "exactly",
    "precisely",
    "agreed",
    "understood",
    "got it",
    "will do",
}

APPROVAL_WORDS = {
    "yes",
    "ok",
    "okay",
    "sure",
    "good",
    "great",
    "fine",
    "nice",
    "perfect",
    "excellent",
    "thanks",
    "approved",
    "continue",
    "proceed",
    "agreed",
    "correct",
    "right",
    "yep",
    "yeah",
}

COMMENCEMENT_PHRASES = [
    "let's continue",
    "let's proceed",
    "let's resume",
    "let's go ahead",
    "let's get started",
    "let's begin",
    "let's start",
    "please continue",
    "please proceed",
    "please resume",
    "please go ahead",
    "yes, let's continue",
    "yes, let's proceed",
    "yes, let's resume",
    "yes, let's begin",
    "yes, let's start",
    "yes, please continue",
    "yes, please proceed",
    "go ahead",
    "go ahead and continue",
    "go ahead and proceed",
    "continue with",
    "proceed with",
]

# Violation detection
VIOLATION_WORDS = {
    "unacceptable",
    "wrong",
    "incorrect",
    "mistake",
    "frustrated",
    "frustrating",
    "annoying",
    "annoyed",
    "disappointed",
    "violation",
    "violate",
    "breach",
    "sloppy",
    "careless",
    "shortcuts",
}
EMPHASIS_VIOLATION_WORDS = {"no", "stop", "bad"}
VIOLATION_BOOST_CATEGORIES = {"trust_execution", "safety_prevention"}
VIOLATION_CATEGORY_BOOST = 20

FOUNDATIONAL_SCORE = 1000
COMMENCEMENT_LOOKBACK_BOOST = 15

# Instruction bundles
INSTRUCTION_BUNDLES = {
    "trust_execution/development_workflow_essentials": [
        ("trust_execution/trust_based_task_execution", 12, 0.55),
    ],
    "trust_execution/trust_based_task_execution": [
        ("trust_execution/development_workflow_essentials", 12, 0.55),
    ],
    "batch_processing_patterns": [
        ("safety_prevention/systematic_prevention_framework", 10, 0.61),
        ("safety_prevention/validation_first_execution", 8, 0.56),
    ],
    "docker_compose_patterns": [
        ("infrastructure/container_management", 15, 0.89),
    ],
    "infrastructure/container_management": [
        ("docker_compose_patterns", 15, 0.89),
        ("mcp_deployment_architecture", 12, 1.00),
    ],
    "mcp_deployment_architecture": [
        ("infrastructure/container_management", 12, 1.00),
    ],
    "github/issue_status_done": [
        ("project_management/issue_closure", 10, 0.62),
    ],
}
BUNDLE_BOOST_BASE = 10

# Semantic flags
SEMANTIC_FLAG_PATTERNS = {
    "corrective": {
        "patterns": [
            r"\bno\b",
            r"\bstop\b",
            r"\bwrong\b",
            r"\bincorrect\b",
            r"\bunacceptable\b",
            r"\bmistake\b",
            r"\berror\b",
            r"\bdon\'t\b",
            r"\bfail\b",
            r"\bbug\b",
        ],
        "boost_categories": ["trust_execution", "learning", "safety_prevention"],
        "boost_amount": 8,
    },
    "directive": {
        "patterns": [
            r"\bplease\s+\w+",
            r"\bshould\b",
            r"\bmust\b",
            r"\bneed\s+to\b",
            r"\bensure\b",
            r"\balways\b",
            r"\bnever\b",
            r"\brequire\b",
        ],
        "boost_categories": [
            "agentic_workflows",
            "safety_prevention",
            "project_management",
        ],
        "boost_amount": 5,
    },
    "compliance": {
        "patterns": [
            r"\bfollow\b",
            r"\badhere\b",
            r"\bcomplian",
            r"\bstandard\b",
            r"\bpolicy\b",
            r"\bprocess\b",
            r"\bworkflow\b",
            r"\bguideline\b",
        ],
        "boost_categories": [
            "safety_prevention",
            "agentic_workflows",
            "trust_execution",
        ],
        "boost_amount": 8,
    },
    "technical": {
        "patterns": [
            r"\bgit\b",
            r"\bgithub\b",
            r"\bdocker\b",
            r"\bcontainer\b",
            r"\bmcp\b",
            r"\bserver\b",
            r"\bapi\b",
            r"\bdatabase\b",
            r"\bdb\b",
        ],
        "boost_categories": ["infrastructure", "github_integration", "devops"],
        "boost_amount": 6,
    },
    "meta": {
        "patterns": [
            r"\bissue\b",
            r"\btask\b",
            r"\bepic\b",
            r"\bsprint\b",
            r"\bmilestone\b",
            r"\bproject\b",
            r"\bstatus\b",
            r"\bclose\b",
            r"\bboard\b",
        ],
        "boost_categories": ["github_integration", "project_management"],
        "boost_amount": 6,
    },
}

COMPILED_SEMANTIC_FLAGS = {
    flag_name: {
        "regex": re.compile("|".join(config["patterns"]), re.IGNORECASE),
        "boost_categories": config["boost_categories"],
        "boost_amount": config["boost_amount"],
    }
    for flag_name, config in SEMANTIC_FLAG_PATTERNS.items()
}

DEFAULT_FEATURES = {
    "violation_detection": True,
    "approval_suppression": True,
    "foundational": True,
    "commencement_lookback": True,
    "instruction_bundles": True,
    "semantic_flags": True,
}


@register_engine(DURIAN_VERSION)
class DurianRouter05(RoutingEngine):
    """
    Frozen stable routing engine (durian-0.5).

    This is the stable version with  through  features,
    preserved for A/B comparison and rollback capability.

    Features:
        - violation_detection:  - Boost compliance on frustration
        - approval_suppression:  - Skip routing for approvals
        - foundational: Always-include foundational instructions
        - commencement_lookback:  - Boost previous on continuation
        - instruction_bundles:  - Boost co-occurring pairs
        - semantic_flags:  - Boost categories by message content
    """

    def __init__(self, handler: InstructionHandler, features: dict | None = None):
        """Initialize router with instruction handler and feature flags."""
        super().__init__(handler)
        self.instruction_handler = handler
        self.features = {**DEFAULT_FEATURES, **(features or {})}
        feature_str = ", ".join(f"{k}={v}" for k, v in self.features.items())
        logger.info(
            f"DurianRouter05 initialized (version: {self.version}, features: {feature_str})"
        )

    @property
    def version(self) -> str:
        """Return frozen engine version identifier."""
        return DURIAN_VERSION

    @property
    def description(self) -> str:
        """Return human-readable description of routing approach."""
        return "Frozen stable: Rule-based routing with  through  features"

    @classmethod
    def get_available_features(cls) -> list[FeatureSpec]:
        """Return feature flags available for durian-0.5."""
        return [
            FeatureSpec(
                name="violation_detection",
                description="Boost compliance routing on frustrated/corrective messages",
                default=True,
                category="scoring",
            ),
            FeatureSpec(
                name="approval_suppression",
                description="Suppress routing for simple approval messages",
                default=True,
                category="routing",
            ),
            FeatureSpec(
                name="foundational",
                description="Always-include foundational instructions",
                default=True,
                category="routing",
            ),
            FeatureSpec(
                name="commencement_lookback",
                description="Boost previous routing on commencement messages",
                default=True,
                category="scoring",
            ),
            FeatureSpec(
                name="instruction_bundles",
                description="Boost co-occurring instruction pairs",
                default=True,
                category="scoring",
            ),
            FeatureSpec(
                name="semantic_flags",
                description="Boost categories based on message semantic flags",
                default=True,
                category="scoring",
            ),
        ]

    def route(self, message: str, context: dict | None = None, limit: int = 5) -> dict:
        """Route message to relevant instruction files."""
        try:
            if self.features.get("approval_suppression", True):
                should_suppress, suppression_reason, commencement_detected = (
                    self._is_simple_approval(message)
                )
                if should_suppress:
                    return {
                        "instructions": [],
                        "count": 0,
                        "routing_analysis": {
                            "suppressed": True,
                            "reason": f"{suppression_reason}",
                            "commencement_detected": False,
                            "message_preview": message[:50]
                            if len(message) > 50
                            else message,
                        },
                    }
            else:
                commencement_detected = False

            commencement_override = (
                commencement_detected
                if self.features.get("approval_suppression", True)
                else None
            )
            keywords = self._extract_keywords(message)
            intent = self._extract_intent(message)

            if self.features.get("violation_detection", True):
                violation_info = self._detect_violations(message)
            else:
                violation_info = {"detected": False, "signals": [], "boost_amount": 0}

            if self.features.get("semantic_flags", True):
                semantic_flags_info = self._detect_semantic_flags(message)
            else:
                semantic_flags_info = {
                    "detected": False,
                    "flags": [],
                    "category_boosts": {},
                }

            context = context or {}
            files = context.get("files", [])
            directories = context.get("directories", [])
            branch = context.get("branch", "")
            language = context.get("language", "")

            previous_routing_ids = set()
            lookback_info = None
            if commencement_detected and self.features.get(
                "commencement_lookback", True
            ):
                lookback_result = self._get_previous_routing(context)
                if lookback_result and lookback_result.get("instructions"):
                    previous_routing_ids = set(lookback_result["instructions"])
                    lookback_info = {
                        "enabled": True,
                        "found": True,
                        "instruction_count": len(previous_routing_ids),
                        "boost_amount": COMMENCEMENT_LOOKBACK_BOOST,
                    }
                else:
                    lookback_info = {"enabled": True, "found": False}
            elif commencement_detected:
                lookback_info = {"enabled": False, "reason": "feature_disabled"}

            scored_instructions = []
            analysis = {
                "keywords_extracted": keywords,
                "intent_detected": intent,
                "context_used": context,
                "features": self.features,
                "violation_detection": violation_info
                if violation_info["detected"]
                else None,
                "semantic_flags": semantic_flags_info
                if semantic_flags_info["detected"]
                else None,
                "commencement_override": commencement_override,
                "commencement_lookback": lookback_info,
                "scoring_breakdown": [],
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
                    violation_info=violation_info,
                    semantic_flags_info=semantic_flags_info,
                )

                if previous_routing_ids:
                    inst_id_normalized = self._normalize_instruction_id(instruction)
                    if inst_id_normalized in previous_routing_ids:
                        score += COMMENCEMENT_LOOKBACK_BOOST
                        score_breakdown["commencement_lookback"] = (
                            COMMENCEMENT_LOOKBACK_BOOST
                        )

                if score > 0:
                    result = instruction.to_dict()
                    result["routing_score"] = score
                    result["score_breakdown"] = score_breakdown
                    scored_instructions.append(result)
                    analysis["scoring_breakdown"].append(
                        {
                            "instruction_id": instruction.id,
                            "score": score,
                            "breakdown": score_breakdown,
                        }
                    )

            if self.features.get("instruction_bundles", True):
                bundle_boost_info = self._apply_bundle_boost(scored_instructions)
                if bundle_boost_info.get("applied"):
                    analysis["bundle_boost"] = bundle_boost_info

            scored_instructions.sort(key=lambda x: x["routing_score"], reverse=True)

            if self.features.get("foundational", True):
                foundational = self._get_foundational_instructions()
                foundational_ids = {inst.get("id") for inst in foundational}
                query_specific = [
                    inst
                    for inst in scored_instructions[:limit]
                    if inst.get("id") not in foundational_ids
                ]
                combined = foundational + query_specific
                analysis["foundational_count"] = len(foundational)
                analysis["foundational_ids"] = list(foundational_ids)
                analysis["query_specific_count"] = len(query_specific)
            else:
                combined = scored_instructions[:limit]
                analysis["foundational_count"] = 0
                analysis["foundational_ids"] = []
                analysis["foundational_disabled"] = True
                analysis["query_specific_count"] = len(combined)

            return {
                "instructions": combined,
                "count": len(combined),
                "routing_analysis": analysis,
            }

        except Exception as e:
            logger.error(f"Error routing message: {e}", exc_info=True)
            return {
                "instructions": [],
                "count": 0,
                "routing_analysis": {"error": str(e)},
            }

    def _detect_violations(self, message: str) -> dict[str, Any]:
        """Detect violation signals in message ()."""
        signals = []
        message_lower = message.lower()
        words = re.findall(r"\b\w+\b", message_lower)
        violation_matches = set(words) & VIOLATION_WORDS
        if violation_matches:
            signals.append(f"violation_words:{','.join(violation_matches)}")

        for word in EMPHASIS_VIOLATION_WORDS:
            if re.search(rf"\b{word.upper()}\b", message):
                signals.append(f"emphasized_{word.upper()}")
            elif re.search(rf"\b{word}\s*!", message_lower):
                signals.append(f"exclaimed_{word}")
            elif re.search(rf"(?:^|[.!?]\s*){word}[,\s]", message_lower):
                signals.append(f"sentence_start_{word}")

        exclaim_count = message.count("!")
        if exclaim_count >= 3:
            signals.append(f"exclamation_density:{exclaim_count}")

        caps_words = [
            w for w in message.split() if w.isupper() and len(w) > 2 and w.isalpha()
        ]
        if len(caps_words) >= 2:
            signals.append(f"caps_emphasis:{','.join(caps_words[:3])}")

        boost_amount = VIOLATION_CATEGORY_BOOST * len(signals) if signals else 0
        return {
            "detected": len(signals) > 0,
            "signals": signals,
            "boost_amount": boost_amount,
        }

    def _is_simple_approval(self, message: str) -> tuple:
        """Detect if message is simple approval ()."""
        message_clean = message.strip().lower()
        message_normalized = re.sub(r"[.!?,]+$", "", message_clean)

        for phrase in COMMENCEMENT_PHRASES:
            if message_clean.startswith(phrase) or f" {phrase}" in message_clean:
                return (False, "commencement_phrase_detected", True)

        if message_normalized in APPROVAL_PATTERNS:
            return (True, "exact_approval_match", False)

        words = message_clean.split()
        if len(words) <= 3:
            if any(word.rstrip(".,!?") in APPROVAL_WORDS for word in words):
                return (True, "short_approval_message", False)

        if len(words) <= 5:
            approval_count = sum(
                1 for word in words if word.rstrip(".,!?") in APPROVAL_WORDS
            )
            if approval_count >= len(words) / 2:
                return (True, "approval_dominated_message", False)

        return (False, "not_approval", False)

    def _get_foundational_instructions(self) -> list[dict]:
        """Return instructions marked as foundational."""
        foundational = []
        for instruction in self.instruction_handler.instructions.values():
            metadata = instruction.metadata or {}
            if metadata.get("foundational", False):
                result = instruction.to_dict()
                result["routing_score"] = FOUNDATIONAL_SCORE
                result["score_breakdown"] = {"foundational": True}
                foundational.append(result)
        return foundational

    def _get_previous_routing(self, context: dict | None = None) -> dict | None:
        """Get previous routing result for commencement look-back ()."""
        if context and "previous_routing" in context:
            return context["previous_routing"]

        db_paths = [
            Path.cwd()
            / ".observability_db"
            / "observability_db-production"
            / "routing_log-production.db",
            Path.cwd().parent
            / ".observability_db"
            / "observability_db-production"
            / "routing_log-production.db",
        ]

        for db_path in db_paths:
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT instruction_ids FROM routing_events
                        WHERE instruction_count > 0
                        ORDER BY timestamp DESC LIMIT 1 OFFSET 1
                    """)
                    row = cursor.fetchone()
                    conn.close()
                    if row and row[0]:
                        return {"instructions": row[0].split(",") if row[0] else []}
                except Exception:
                    continue
        return None

    def _normalize_instruction_id(self, instruction) -> str:
        """Normalize instruction ID to category/name format ()."""
        inst_id = instruction.id
        if inst_id.endswith(".instructions"):
            inst_id = inst_id[: -len(".instructions")]
        categories = instruction.categories or []
        return f"{categories[0]}/{inst_id}" if categories else inst_id

    def _extract_keywords(self, message: str) -> list[str]:
        """Extract keywords from message."""
        message_lower = message.lower()
        message_clean = re.sub(r"[^\w\s]", " ", message_lower)
        words = message_clean.split()
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _extract_intent(self, message: str) -> str:
        """Extract intent from message."""
        message_lower = message.lower()
        if any(word in message_lower for word in ["how do i", "how to", "how can"]):
            return "how-to"
        elif any(word in message_lower for word in ["what is", "what are", "explain"]):
            return "explanation"
        elif any(word in message_lower for word in ["create", "add", "make", "build"]):
            return "creation"
        elif any(
            word in message_lower
            for word in ["fix", "debug", "error", "issue", "problem"]
        ):
            return "troubleshooting"
        elif any(word in message_lower for word in ["test", "validate", "check"]):
            return "validation"
        elif any(
            word in message_lower for word in ["document", "write docs", "readme"]
        ):
            return "documentation"
        return "general"

    def _score_instruction(
        self,
        instruction,
        message: str,
        keywords: list[str],
        intent: str,
        files: list[str],
        directories: list[str],
        branch: str,
        language: str,
        violation_info: dict | None = None,
        semantic_flags_info: dict | None = None,
    ) -> tuple[int, dict]:
        """Score instruction relevance using multiple signals."""
        score = 0
        breakdown = {}

        if violation_info and violation_info.get("detected"):
            for category in instruction.categories:
                if category in VIOLATION_BOOST_CATEGORIES:
                    score += violation_info["boost_amount"]
                    breakdown["violation_boost"] = {
                        "category": category,
                        "boost": violation_info["boost_amount"],
                        "signals": violation_info["signals"],
                    }
                    break

        if semantic_flags_info and semantic_flags_info.get("detected"):
            category_boosts = semantic_flags_info.get("category_boosts", {})
            for category in instruction.categories:
                if category in category_boosts:
                    boost = category_boosts[category]
                    score += boost
                    if "semantic_flag_boost" not in breakdown:
                        breakdown["semantic_flag_boost"] = []
                    breakdown["semantic_flag_boost"].append(
                        {
                            "category": category,
                            "boost": boost,
                            "flags": semantic_flags_info.get("flags", []),
                        }
                    )

        keyword_matches = []
        for keyword in keywords:
            if keyword in instruction.id.lower():
                score += 10
                keyword_matches.append(f"id:{keyword}")
            if keyword in instruction.description.lower():
                score += 8
                keyword_matches.append(f"description:{keyword}")
            for tag in instruction.tags:
                if keyword in tag.lower():
                    score += 5
                    keyword_matches.append(f"tag:{tag}")
            routing = instruction.routing or {}
            triggers = routing.get("triggers", {})
            meta_keywords = triggers.get("keywords", [])
            for meta_keyword in meta_keywords:
                if keyword in meta_keyword.lower():
                    score += 10
                    keyword_matches.append(f"metadata_keyword:{meta_keyword}")

        if keyword_matches:
            breakdown["keyword_matches"] = keyword_matches

        category_matches = []
        for category in instruction.categories:
            if any(keyword in category.lower() for keyword in keywords):
                score += 5
                category_matches.append(category)
        if category_matches:
            breakdown["category_matches"] = category_matches

        routing = instruction.routing or {}
        triggers = routing.get("triggers", {})
        nlp_trigger = triggers.get("nlp", "")
        if nlp_trigger:
            nlp_keywords = self._extract_keywords(nlp_trigger)
            overlap = set(keywords) & set(nlp_keywords)
            if overlap:
                score += 8 * len(overlap)
                breakdown["nlp_trigger_match"] = list(overlap)

        glob_matches = []
        apply_to = routing.get("applyTo", {})
        globs = apply_to.get("globs", [])
        for file_path in files:
            for glob_pattern in globs:
                if fnmatch.fnmatch(file_path, glob_pattern):
                    score += 7
                    glob_matches.append(f"{file_path} matches {glob_pattern}")
        if glob_matches:
            breakdown["glob_matches"] = glob_matches

        contextual_matches = []
        contextual = routing.get("contextual", {})
        file_patterns = contextual.get("files", [])
        for file_path in files:
            for pattern in file_patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    score += 5
                    contextual_matches.append(f"file_context:{file_path}")
        branch_patterns = contextual.get("branches", [])
        for pattern in branch_patterns:
            if fnmatch.fnmatch(branch, pattern):
                score += 5
                contextual_matches.append(f"branch_context:{branch}")
        if contextual_matches:
            breakdown["contextual_matches"] = contextual_matches

        tag_matches = []
        for tag in instruction.tags:
            if any(keyword in tag.lower() for keyword in keywords):
                score += 3
                tag_matches.append(tag)
        if tag_matches:
            breakdown["tag_matches"] = tag_matches

        breakdown["total_score"] = score
        return score, breakdown

    def _detect_semantic_flags(self, message: str) -> dict[str, Any]:
        """Detect semantic flags in message ()."""
        flags = []
        category_boosts = {}
        for flag_name, config in COMPILED_SEMANTIC_FLAGS.items():
            if config["regex"].search(message):
                flags.append(flag_name)
                for category in config["boost_categories"]:
                    if category not in category_boosts:
                        category_boosts[category] = 0
                    category_boosts[category] += config["boost_amount"]
        return {
            "detected": len(flags) > 0,
            "flags": flags,
            "category_boosts": category_boosts,
        }

    def _apply_bundle_boost(self, scored_instructions: list[dict]) -> dict[str, Any]:
        """Apply bundle boost for co-occurring instruction pairs ()."""
        boosts_applied = []
        instruction_ids = set()
        for inst in scored_instructions:
            inst_id = inst.get("id", "")
            categories = inst.get("categories", [])
            if categories and "/" not in inst_id:
                normalized_id = f"{categories[0]}/{inst_id}"
            else:
                normalized_id = inst_id
            instruction_ids.add(normalized_id)
            if normalized_id.endswith(".instructions"):
                instruction_ids.add(normalized_id[: -len(".instructions")])

        for inst in scored_instructions:
            inst_id = inst.get("id", "")
            categories = inst.get("categories", [])
            ids_to_check = [inst_id]
            if categories:
                ids_to_check.append(f"{categories[0]}/{inst_id}")
            if inst_id.endswith(".instructions"):
                ids_to_check.append(inst_id[: -len(".instructions")])
                if categories:
                    ids_to_check.append(
                        f"{categories[0]}/{inst_id[:-len('.instructions')]}"
                    )

            for id_format in ids_to_check:
                if id_format in INSTRUCTION_BUNDLES:
                    bundle_partners = INSTRUCTION_BUNDLES[id_format]
                    for partner_id, boost_amount, co_occurrence_rate in bundle_partners:
                        if partner_id in instruction_ids:
                            for partner_inst in scored_instructions:
                                p_id = partner_inst.get("id", "")
                                p_categories = partner_inst.get("categories", [])
                                p_normalized = (
                                    f"{p_categories[0]}/{p_id}"
                                    if p_categories
                                    else p_id
                                )
                                if partner_id in (p_id, p_normalized):
                                    partner_inst["routing_score"] += boost_amount
                                    if "score_breakdown" not in partner_inst:
                                        partner_inst["score_breakdown"] = {}
                                    partner_inst["score_breakdown"]["bundle_boost"] = {
                                        "from": id_format,
                                        "boost": boost_amount,
                                        "co_occurrence_rate": co_occurrence_rate,
                                    }
                                    boosts_applied.append(
                                        {
                                            "trigger": id_format,
                                            "boosted": partner_id,
                                            "amount": boost_amount,
                                        }
                                    )
                                    break
                    break

        return {
            "applied": len(boosts_applied) > 0,
            "boosts": boosts_applied,
            "total_boosts": len(boosts_applied),
        }
