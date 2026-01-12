"""
DEPRECATED: This module is deprecated. Use pongogo_router instead.

This module exists for backwards compatibility only.
All functionality has been moved to pongogo_router.py.

Migration:
    # Old (deprecated)
    from mcp_server.router import RuleBasedRouter, InstructionRouter

    # New (recommended)
    from mcp_server.pongogo_router import RuleBasedRouter, InstructionRouter

This shim will be removed in a future version.
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "mcp_server.router is deprecated. Use mcp_server.pongogo_router instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from pongogo_router for backwards compatibility
from mcp_server.pongogo_router import (  # noqa: F401, E402
    APPROVAL_PATTERNS,
    BOUNDARY_PATTERNS,
    DEFAULT_FEATURES,
    DURIAN_VERSION,
    FRICTION_PATTERNS,
    LIFECYCLE_KEYWORDS,
    MISTAKE_PATTERNS,
    InstructionRouter,
    RuleBasedRouter,
)
