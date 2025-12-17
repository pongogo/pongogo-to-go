"""Frozen Routing Engine Versions

This directory contains frozen/snapshot versions of the durian routing engine.
Each frozen version is registered via the @register_engine decorator and can
be selected at runtime for evaluation and A/B testing.

Architecture Principle: Routing Engine Independence
- durian is knowledge-source agnostic (works across different instruction file sets)
- durian is knowledge-recipient agnostic (works with any coding companion)
- Evaluations compare algorithm versions against CURRENT instruction files

Naming Convention:
- Class: DurianRouterXX (e.g., DurianRouter00, DurianRouter05)
- Version string: durian-XX (e.g., durian-00, durian-0.5)
- File: durian_XX.py (e.g., durian_00.py, durian_05.py)

Usage:
    from routing_engine import create_router, get_available_engines

    # List available engines
    engines = get_available_engines()  # ['durian-00', 'durian-0.5-dev', ...]

    # Create specific engine
    router = create_router(handler, {"routing": {"engine": "durian-00"}})

References:
    - Spike #188: Routing Engine Architecture
    - Task #214: RoutingEngine Abstract Interface
    - Task #231: Version Snapshot Infrastructure
"""

from pathlib import Path
import importlib
import logging

logger = logging.getLogger(__name__)

# Auto-import all durian_*.py files to trigger @register_engine decorators
engines_dir = Path(__file__).parent
for engine_file in engines_dir.glob("durian_*.py"):
    module_name = engine_file.stem
    try:
        importlib.import_module(f".{module_name}", package=__name__)
        logger.debug(f"Loaded routing engine module: {module_name}")
    except ImportError as e:
        logger.warning(f"Failed to load routing engine module {module_name}: {e}")
