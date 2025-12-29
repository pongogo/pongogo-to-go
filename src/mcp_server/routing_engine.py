"""Routing Engine Abstract Interface

Defines the abstract interface for swappable routing engines (durian versions).
Part of the Routing Engine Architecture.

Architecture:
    IDE/Coding Tool → LLM → MCP Tools → Pongogo MCP Server → RoutingEngine

    The RoutingEngine interface enables routing algorithm evolution without
    affecting layers above. Pongogo is LLM-agnostic and IDE-agnostic.

Versions:
    - durian-00: Rule-based routing (keyword, category, pattern matching)
    - durian-01: Rule-based + TF-IDF semantic matching (planned)
    - durian-02: Embedding-based semantic similarity (future)

References:
    - Routing Engine Architecture
    - Create RoutingEngine Abstract Interface
    - docs/architecture/routing_engine_interface.md
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from mcp_server.instruction_handler import InstructionHandler


class RoutingError(Exception):
    """Raised when routing cannot complete due to system error."""
    pass


class ConfigurationError(Exception):
    """Raised when routing configuration is invalid."""
    pass


class FeatureSpec:
    """Specification for a feature flag."""

    def __init__(
        self,
        name: str,
        description: str,
        default: bool = True,
        category: str = "general"
    ):
        """
        Define a feature flag specification.

        Args:
            name: Feature identifier (e.g., "violation_detection")
            description: Human-readable description
            default: Default value (True = enabled by default)
            category: Grouping category (e.g., "routing", "scoring")
        """
        self.name = name
        self.description = description
        self.default = default
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "default": self.default,
            "category": self.category,
        }


class RoutingEngine(ABC):
    """
    Abstract interface for routing engines (durian versions).

    All routing engine implementations must inherit from this class and
    implement the abstract methods. This enables swappable engines at
    the server level without modifying the MCP interface.

    Attributes:
        handler: InstructionHandler providing access to knowledge base
    """

    def __init__(self, handler: InstructionHandler):
        """
        Initialize routing engine with instruction handler.

        Args:
            handler: InstructionHandler instance providing access to knowledge base
        """
        self.handler = handler

    @abstractmethod
    def route(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Route a message to relevant instructions.

        Args:
            message: User message or query to route
            context: Optional context dictionary with:
                - files: List of file paths in current context
                - directories: List of directory paths
                - branch: Current git branch
                - language: Programming language
            limit: Maximum number of instructions to return

        Returns:
            Dictionary with:
                - instructions: List of matched instructions with scores
                - count: Number of results
                - routing_analysis: Breakdown of routing decision

        Raises:
            RoutingError: If routing cannot complete due to system error
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Return engine version identifier.

        Format: 'durian-XX' where XX is version number.
        Examples: 'durian-00', 'durian-01', 'durian-02'
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return human-readable description of routing approach."""
        pass

    @classmethod
    def get_available_features(cls) -> List[FeatureSpec]:
        """
        Return list of feature flags available for this engine.

        Override in subclasses to declare engine-specific feature flags.
        Default implementation returns empty list (no configurable features).

        Returns:
            List of FeatureSpec objects describing available features

        Example:
            @classmethod
            def get_available_features(cls) -> List[FeatureSpec]:
                return [
                    FeatureSpec("violation_detection", "Boost compliance routing", True),
                    FeatureSpec("approval_suppression", "Suppress approval messages", True),
                ]
        """
        return []

    @classmethod
    def get_default_features(cls) -> Dict[str, bool]:
        """
        Return dict of feature defaults for this engine.

        Returns:
            Dict mapping feature name to default value
        """
        return {f.name: f.default for f in cls.get_available_features()}


# Engine registry for factory function
_ENGINE_REGISTRY: Dict[str, type] = {}


def register_engine(version: str):
    """
    Decorator to register a routing engine implementation.

    Usage:
        @register_engine("durian-00")
        class RuleBasedRouter(RoutingEngine):
            ...

    Args:
        version: Engine version identifier (e.g., 'durian-00')

    Returns:
        Decorator function that registers the class
    """
    def decorator(cls):
        _ENGINE_REGISTRY[version] = cls
        return cls
    return decorator


# Default engine version - set after router module registers its engine
# This allows the factory to work without hardcoding the version here
DEFAULT_ENGINE_VERSION: Optional[str] = None


def set_default_engine(version: str):
    """Set the default engine version for the factory function."""
    global DEFAULT_ENGINE_VERSION
    DEFAULT_ENGINE_VERSION = version


def get_default_engine() -> str:
    """Get the default engine version, falling back to first registered if not set."""
    if DEFAULT_ENGINE_VERSION and DEFAULT_ENGINE_VERSION in _ENGINE_REGISTRY:
        return DEFAULT_ENGINE_VERSION
    # Fall back to first registered engine
    if _ENGINE_REGISTRY:
        return next(iter(_ENGINE_REGISTRY.keys()))
    raise ConfigurationError("No routing engines registered")


def create_router(
    handler: InstructionHandler,
    config: Optional[Dict[str, Any]] = None
) -> RoutingEngine:
    """
    Factory function to create routing engine based on configuration.

    Creates the appropriate routing engine implementation based on
    configuration. Defaults to the registered default engine if no
    config provided.

    Args:
        handler: InstructionHandler instance
        config: Optional configuration dictionary with:
            - routing.engine: Engine version (uses default if not specified)
            - routing.features: Feature flags dict ():
                - violation_detection: bool ()
                - approval_suppression: bool ()
                - foundational: bool (always-include foundational)

    Returns:
        RoutingEngine implementation instance

    Raises:
        ConfigurationError: If requested engine version is unknown

    Examples:
        # Default engine
        router = create_router(handler)

        # Explicit version
        router = create_router(handler, {"routing": {"engine": "durian-01"}})

        # With feature flags ()
        router = create_router(handler, {"routing": {
            "engine": "durian-0.5",
            "features": {"violation_detection": False}
        }})
    """
    # Get default from registry if not specified in config
    default_version = get_default_engine()
    engine_version = default_version
    features = None
    if config:
        routing_config = config.get("routing", {})
        # Use 'or' to handle None values from config (not just missing keys)
        engine_version = routing_config.get("engine") or default_version
        features = routing_config.get("features")  # 

    # Look up engine class in registry
    if engine_version not in _ENGINE_REGISTRY:
        available = list(_ENGINE_REGISTRY.keys())
        raise ConfigurationError(
            f"Unknown routing engine: '{engine_version}'. "
            f"Available engines: {available}"
        )

    # Validate features against engine's available features
    if features:
        validate_features(engine_version, features)

    # Create and return engine instance
    # Pass features if engine supports it (duck typing)
    engine_class = _ENGINE_REGISTRY[engine_version]
    try:
        # Try with features ( - RuleBasedRouter supports this)
        return engine_class(handler, features=features)
    except TypeError:
        # Fall back for engines that don't support features parameter
        if features:
            # Engine doesn't support features but features were requested
            raise ConfigurationError(
                f"Engine '{engine_version}' does not support feature flags. "
                f"Remove --enable-*/--disable-* flags or choose a different engine."
            )
        return engine_class(handler)


def get_available_engines() -> List[str]:
    """
    Return list of available engine versions.

    Returns:
        List of registered engine version identifiers
    """
    return list(_ENGINE_REGISTRY.keys())


def get_engine_features(version: str) -> List[FeatureSpec]:
    """
    Get available feature flags for a specific engine version.

    Args:
        version: Engine version identifier (e.g., "durian-0.5")

    Returns:
        List of FeatureSpec objects for the engine

    Raises:
        ConfigurationError: If engine version is unknown
    """
    if version not in _ENGINE_REGISTRY:
        available = list(_ENGINE_REGISTRY.keys())
        raise ConfigurationError(
            f"Unknown routing engine: '{version}'. "
            f"Available engines: {available}"
        )

    engine_class = _ENGINE_REGISTRY[version]
    return engine_class.get_available_features()


def get_engine_default_features(version: str) -> Dict[str, bool]:
    """
    Get default feature values for a specific engine version.

    Args:
        version: Engine version identifier

    Returns:
        Dict mapping feature name to default value
    """
    if version not in _ENGINE_REGISTRY:
        return {}

    engine_class = _ENGINE_REGISTRY[version]
    return engine_class.get_default_features()


def validate_features(version: str, features: Dict[str, bool]) -> None:
    """
    Validate that provided features are valid for the engine.

    Args:
        version: Engine version identifier
        features: Dict of feature flags to validate

    Raises:
        ConfigurationError: If any feature is not available for this engine
    """
    available_features = get_engine_features(version)
    available_names = {f.name for f in available_features}

    for feature_name in features.keys():
        if feature_name not in available_names:
            raise ConfigurationError(
                f"Feature '{feature_name}' is not available for engine '{version}'. "
                f"Available features: {sorted(available_names) if available_names else '(none)'}"
            )
