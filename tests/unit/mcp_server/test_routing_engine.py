"""Unit tests for MCP server routing_engine module.

Tests the abstract RoutingEngine interface, registry, and factory function.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.routing_engine import (
    _ENGINE_REGISTRY,
    ConfigurationError,
    FeatureSpec,
    RoutingEngine,
    create_router,
    get_available_engines,
    get_default_engine,
    get_engine_default_features,
    get_engine_features,
    register_engine,
    set_default_engine,
    validate_features,
)


class TestFeatureSpec:
    """Tests for FeatureSpec class."""

    def test_feature_spec_creation(self):
        """Create FeatureSpec with all parameters."""
        spec = FeatureSpec(
            name="test_feature",
            description="Test description",
            default=True,
            category="testing",
        )

        assert spec.name == "test_feature"
        assert spec.description == "Test description"
        assert spec.default is True
        assert spec.category == "testing"

    def test_feature_spec_defaults(self):
        """Create FeatureSpec with defaults."""
        spec = FeatureSpec("minimal", "Minimal spec")

        assert spec.default is True  # default
        assert spec.category == "general"  # default

    def test_feature_spec_to_dict(self):
        """Convert FeatureSpec to dictionary."""
        spec = FeatureSpec("test", "Test", default=False, category="routing")

        result = spec.to_dict()

        assert result == {
            "name": "test",
            "description": "Test",
            "default": False,
            "category": "routing",
        }


class TestRoutingEngineInterface:
    """Tests for RoutingEngine abstract class."""

    def test_routing_engine_is_abstract(self):
        """RoutingEngine should not be instantiable directly."""
        mock_handler = MagicMock()

        with pytest.raises(TypeError):
            RoutingEngine(mock_handler)

    def test_subclass_must_implement_route(self):
        """Subclass must implement route method."""

        class IncompleteEngine(RoutingEngine):
            @property
            def version(self) -> str:
                return "test-1.0"

            @property
            def description(self) -> str:
                return "Test engine"

        mock_handler = MagicMock()

        with pytest.raises(TypeError):
            IncompleteEngine(mock_handler)

    def test_subclass_must_implement_version(self):
        """Subclass must implement version property."""

        class IncompleteEngine(RoutingEngine):
            def route(self, message: str, context=None, limit=5):
                return {}

            @property
            def description(self) -> str:
                return "Test engine"

        mock_handler = MagicMock()

        with pytest.raises(TypeError):
            IncompleteEngine(mock_handler)

    def test_get_available_features_default(self):
        """Default get_available_features returns empty list."""

        class MinimalEngine(RoutingEngine):
            def route(self, message: str, context=None, limit=5):
                return {}

            @property
            def version(self) -> str:
                return "test-1.0"

            @property
            def description(self) -> str:
                return "Test"

        assert MinimalEngine.get_available_features() == []

    def test_get_default_features(self):
        """get_default_features returns dict from specs."""

        class FeatureEngine(RoutingEngine):
            def route(self, message: str, context=None, limit=5):
                return {}

            @property
            def version(self) -> str:
                return "test-1.0"

            @property
            def description(self) -> str:
                return "Test"

            @classmethod
            def get_available_features(cls):
                return [
                    FeatureSpec("feature_a", "Feature A", default=True),
                    FeatureSpec("feature_b", "Feature B", default=False),
                ]

        result = FeatureEngine.get_default_features()

        assert result == {"feature_a": True, "feature_b": False}


class TestEngineRegistry:
    """Tests for engine registration and lookup."""

    def test_register_engine_decorator(self):
        """register_engine decorator adds to registry."""
        # Save original registry state
        original_registry = _ENGINE_REGISTRY.copy()

        try:

            @register_engine("test-engine-001")
            class TestEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "test-engine-001"

                @property
                def description(self) -> str:
                    return "Test"

            assert "test-engine-001" in _ENGINE_REGISTRY
            assert _ENGINE_REGISTRY["test-engine-001"] == TestEngine
        finally:
            # Restore registry
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)

    def test_get_available_engines(self):
        """get_available_engines returns registered versions."""
        result = get_available_engines()

        assert isinstance(result, list)
        # Should return whatever engines are registered
        # (depends on imports)


class TestDefaultEngine:
    """Tests for default engine handling."""

    def test_set_and_get_default_engine(self):
        """set_default_engine and get_default_engine work together."""
        # Save original state
        original_registry = _ENGINE_REGISTRY.copy()

        try:
            # Register a test engine
            @register_engine("test-default-engine")
            class TestDefaultEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "test-default-engine"

                @property
                def description(self) -> str:
                    return "Test"

            set_default_engine("test-default-engine")
            result = get_default_engine()

            assert result == "test-default-engine"
        finally:
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)

    def test_get_default_falls_back_to_first(self):
        """get_default_engine falls back to first registered."""
        original_registry = _ENGINE_REGISTRY.copy()

        try:
            _ENGINE_REGISTRY.clear()

            @register_engine("first-engine")
            class FirstEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "first-engine"

                @property
                def description(self) -> str:
                    return "First"

            # Don't set default explicitly

            # Clear default
            with patch("mcp_server.routing_engine.DEFAULT_ENGINE_VERSION", None):
                result = get_default_engine()
                assert result == "first-engine"
        finally:
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)


class TestCreateRouter:
    """Tests for create_router factory function."""

    def test_create_router_unknown_engine_raises(self):
        """create_router raises for unknown engine version."""
        original_registry = _ENGINE_REGISTRY.copy()

        try:
            # Register a dummy engine so get_default_engine doesn't fail first
            @register_engine("dummy-engine")
            class DummyEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "dummy-engine"

                @property
                def description(self) -> str:
                    return "Dummy"

            mock_handler = MagicMock()
            config = {"routing": {"engine": "nonexistent-engine"}}

            with pytest.raises(ConfigurationError, match="Unknown routing engine"):
                create_router(mock_handler, config)
        finally:
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)


class TestValidateFeatures:
    """Tests for validate_features function."""

    def test_validate_unknown_feature_raises(self):
        """validate_features raises for unknown feature."""
        original_registry = _ENGINE_REGISTRY.copy()

        try:

            @register_engine("feature-test-engine")
            class FeatureTestEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "feature-test-engine"

                @property
                def description(self) -> str:
                    return "Test"

                @classmethod
                def get_available_features(cls):
                    return [FeatureSpec("known_feature", "Known")]

            with pytest.raises(ConfigurationError, match="not available"):
                validate_features("feature-test-engine", {"unknown_feature": True})
        finally:
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)

    def test_validate_known_feature_passes(self):
        """validate_features passes for known features."""
        original_registry = _ENGINE_REGISTRY.copy()

        try:

            @register_engine("known-feature-engine")
            class KnownFeatureEngine(RoutingEngine):
                def route(self, message: str, context=None, limit=5):
                    return {}

                @property
                def version(self) -> str:
                    return "known-feature-engine"

                @property
                def description(self) -> str:
                    return "Test"

                @classmethod
                def get_available_features(cls):
                    return [FeatureSpec("known_feature", "Known")]

            # Should not raise
            validate_features("known-feature-engine", {"known_feature": True})
        finally:
            _ENGINE_REGISTRY.clear()
            _ENGINE_REGISTRY.update(original_registry)


class TestGetEngineFeatures:
    """Tests for get_engine_features function."""

    def test_get_engine_features_unknown_raises(self):
        """get_engine_features raises for unknown engine."""
        with pytest.raises(ConfigurationError, match="Unknown routing engine"):
            get_engine_features("nonexistent-engine")


class TestGetEngineDefaultFeatures:
    """Tests for get_engine_default_features function."""

    def test_get_engine_default_features_unknown_returns_empty(self):
        """get_engine_default_features returns {} for unknown engine."""
        result = get_engine_default_features("nonexistent-engine")
        assert result == {}
