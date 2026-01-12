#!/usr/bin/env python3
"""
Diagnostic script for guidance detection issues.

Run this to capture the state of guidance detection in pongogo-to-go.
Outputs diagnostic info to help debug why guidance_action might not be emitted.

Usage:
    python scripts/diagnose_guidance.py
    python scripts/diagnose_guidance.py "Here are some general guidelines to follow"
"""

import json
import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


def diagnose():
    """Run diagnostics and output results."""
    results = {"diagnostics_version": "1.0.0", "checks": {}}

    # Test message
    test_message = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Here are some general guidelines to follow"
    )
    results["test_message"] = test_message

    # Check 1: Router version
    try:
        from mcp_server.pongogo_router import DURIAN_VERSION

        results["checks"]["router_version"] = {
            "status": "ok",
            "version": DURIAN_VERSION,
        }
    except Exception as e:
        results["checks"]["router_version"] = {"status": "error", "error": str(e)}

    # Check 2: Lexicon DB availability
    try:
        from mcp_server.pongogo_router import (
            DEFAULT_DB_PATH,
            LEXICON_AVAILABLE,
            LEXICON_DB_AVAILABLE,
        )

        results["checks"]["lexicon_availability"] = {
            "status": "ok",
            "LEXICON_DB_AVAILABLE": LEXICON_DB_AVAILABLE,
            "LEXICON_AVAILABLE": LEXICON_AVAILABLE,
            "DEFAULT_DB_PATH": str(DEFAULT_DB_PATH) if DEFAULT_DB_PATH else None,
            "db_exists": DEFAULT_DB_PATH.exists() if DEFAULT_DB_PATH else False,
        }
    except Exception as e:
        results["checks"]["lexicon_availability"] = {"status": "error", "error": str(e)}

    # Check 3: Context disambiguation availability
    try:
        from mcp_server.pongogo_router import (
            CONTEXT_DISAMBIGUATION_AVAILABLE,
            match_all_entries,
        )

        results["checks"]["context_disambiguation"] = {
            "status": "ok",
            "CONTEXT_DISAMBIGUATION_AVAILABLE": CONTEXT_DISAMBIGUATION_AVAILABLE,
            "match_all_entries_available": match_all_entries is not None,
        }
    except Exception as e:
        results["checks"]["context_disambiguation"] = {
            "status": "error",
            "error": str(e),
        }

    # Check 4: Lexicon patterns for guidelines
    try:
        from mcp_server.lexicon_db import DEFAULT_DB_PATH, LexiconDB

        if DEFAULT_DB_PATH and DEFAULT_DB_PATH.exists():
            db = LexiconDB()
            # Get guidance entries
            guidance_entries = db.get_entries_by_type("guidance")
            guideline_patterns = [
                e
                for e in guidance_entries
                if "guideline" in str(e.pattern).lower()
                or "here" in str(e.pattern).lower()
            ]
            results["checks"]["lexicon_patterns"] = {
                "status": "ok",
                "total_guidance_entries": len(guidance_entries),
                "guideline_patterns": [
                    {"id": e.id, "pattern": str(e.pattern), "category": e.category}
                    for e in guideline_patterns[:10]  # Limit output
                ],
            }
        else:
            results["checks"]["lexicon_patterns"] = {
                "status": "skip",
                "reason": "Lexicon DB not found",
            }
    except Exception as e:
        results["checks"]["lexicon_patterns"] = {"status": "error", "error": str(e)}

    # Check 5: Hardcoded patterns
    try:
        from mcp_server.pongogo_router import EXPLICIT_GUIDANCE_TRIGGERS

        guideline_in_hardcoded = any(
            "guideline" in p.lower() or "here\\s+are" in p.lower()
            for p in EXPLICIT_GUIDANCE_TRIGGERS
        )
        results["checks"]["hardcoded_patterns"] = {
            "status": "ok",
            "total_patterns": len(EXPLICIT_GUIDANCE_TRIGGERS),
            "has_guideline_pattern": guideline_in_hardcoded,
            "sample_patterns": list(EXPLICIT_GUIDANCE_TRIGGERS)[:5],
        }
    except Exception as e:
        results["checks"]["hardcoded_patterns"] = {"status": "error", "error": str(e)}

    # Check 6: Default features
    try:
        from mcp_server.pongogo_router import DEFAULT_FEATURES

        guidance_features = {
            k: v
            for k, v in DEFAULT_FEATURES.items()
            if "guidance" in k.lower() or "lexicon" in k.lower()
        }
        results["checks"]["feature_flags"] = {
            "status": "ok",
            "guidance_related_features": guidance_features,
        }
    except Exception as e:
        results["checks"]["feature_flags"] = {"status": "error", "error": str(e)}

    # Check 7: Test actual routing
    try:
        from mcp_server.instruction_handler import InstructionHandler
        from mcp_server.pongogo_router import InstructionRouter

        # Find knowledge base - check multiple possible locations
        server_dir = SRC_DIR / "mcp_server"
        possible_kb_paths = [
            Path(__file__).parent.parent / "instructions",  # pongogo-to-go/instructions
            server_dir / "instructions",  # src/mcp_server/instructions
            Path("/knowledge/instructions"),  # Docker mount
        ]

        kb_path = None
        for p in possible_kb_paths:
            if p.exists():
                kb_path = p
                break

        if not kb_path:
            raise ValueError(f"Knowledge base not found. Checked: {possible_kb_paths}")

        # Get core path (bundled instructions)
        core_path = server_dir / "core_instructions"
        if not core_path.exists():
            core_path = None

        handler = InstructionHandler(kb_path, core_path=core_path)
        count = handler.load_instructions()

        router = InstructionRouter(handler)

        # Check if lexicon was loaded
        lexicon_loaded = hasattr(router, "_lexicon_entries") and router._lexicon_entries

        # Run routing
        result = router.route(test_message, limit=3)

        results["checks"]["routing_test"] = {
            "status": "ok",
            "instructions_loaded": count,
            "lexicon_entries_loaded": len(router._lexicon_entries)
            if lexicon_loaded
            else 0,
            "routing_engine_version": router.version,
            "guidance_action_present": result.get("guidance_action") is not None,
            "guidance_action": result.get("guidance_action"),
            "routing_analysis_guidance_pre_check": result.get(
                "routing_analysis", {}
            ).get("guidance_pre_check"),
            "instructions_routed": result.get("count", 0),
        }
    except Exception as e:
        import traceback

        results["checks"]["routing_test"] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # Check 8: Pattern matching test
    try:
        import re

        pattern = r"here\s+are\s+(?:some\s+)?(?:general\s+)?(?:guidelines|rules)"
        match = re.search(pattern, test_message, re.IGNORECASE)
        results["checks"]["pattern_match_test"] = {
            "status": "ok",
            "pattern": pattern,
            "message": test_message,
            "matches": match is not None,
            "match_text": match.group() if match else None,
        }
    except Exception as e:
        results["checks"]["pattern_match_test"] = {"status": "error", "error": str(e)}

    # Output results
    print(json.dumps(results, indent=2, default=str))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for check_name, check_result in results["checks"].items():
        status = check_result.get("status", "unknown")
        icon = "✅" if status == "ok" else "❌" if status == "error" else "⚠️"
        print(f"{icon} {check_name}: {status}")

        # Highlight key findings
        if check_name == "routing_test" and status == "ok":
            if check_result.get("guidance_action_present"):
                print("   → guidance_action: PRESENT")
            else:
                print("   → guidance_action: MISSING ⚠️")

    # Return exit code
    routing_check = results["checks"].get("routing_test", {})
    if routing_check.get("status") == "ok" and routing_check.get(
        "guidance_action_present"
    ):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(diagnose())
