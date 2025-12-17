"""Pongogo Knowledge Server Configuration

Configuration loading with environment variable support and sensible defaults.
Implements Task #213: Add engine selection configuration support.

Environment Variables:
    PONGOGO_CONFIG_PATH: Path to config file (default: pongogo-config.yaml in server dir)
    PONGOGO_KNOWLEDGE_PATH: Override knowledge base path from config

Configuration Schema:
    routing:
        engine: str - Engine version (e.g., "durian-0.5")
        limit_default: int - Default routing limit (default: 5)
        features: dict - Feature flags for engine (e.g., {"violation_detection": True})
    knowledge:
        path: str - Path to knowledge/instructions directory
    server:
        log_level: str - Logging level (default: "INFO")
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""
    pass


# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "routing": {
        "engine": None,  # Use registered default engine
        "limit_default": 5,
        "features": {},  # No feature overrides
    },
    "knowledge": {
        "path": None,  # Use default path relative to server
    },
    "server": {
        "log_level": "INFO",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge override dict into base dict.

    Args:
        base: Base dictionary (defaults)
        override: Override dictionary (user config)

    Returns:
        Merged dictionary with override values taking precedence
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_path(path: Optional[str], base_dir: Path) -> Optional[Path]:
    """
    Resolve a path, making relative paths absolute from base_dir.

    Args:
        path: Path string (absolute or relative) or None
        base_dir: Base directory for relative path resolution

    Returns:
        Resolved absolute Path or None if path was None
    """
    if path is None:
        return None

    path_obj = Path(path)
    if path_obj.is_absolute():
        return path_obj
    return (base_dir / path_obj).resolve()


def load_config(
    config_path: Optional[str] = None,
    server_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable overrides.

    Configuration Loading Order (later overrides earlier):
    1. Default values (DEFAULT_CONFIG)
    2. Config file (from PONGOGO_CONFIG_PATH or config_path parameter)
    3. Environment variable overrides (PONGOGO_KNOWLEDGE_PATH)

    Args:
        config_path: Explicit config file path (overrides PONGOGO_CONFIG_PATH)
        server_dir: Server directory for relative path resolution

    Returns:
        Merged configuration dictionary

    Raises:
        ConfigurationError: If config file exists but is invalid YAML

    Examples:
        # Load with defaults (no config file required)
        config = load_config()

        # Load from specific file
        config = load_config("/path/to/pongogo-config.yaml")

        # Load with environment variable
        os.environ["PONGOGO_CONFIG_PATH"] = "/path/to/config.yaml"
        config = load_config()
    """
    # Determine server directory for path resolution
    if server_dir is None:
        server_dir = Path(__file__).parent

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Determine config file path
    file_path = config_path or os.environ.get("PONGOGO_CONFIG_PATH")

    if file_path:
        # Explicit config path - must exist and be valid
        resolved_path = _resolve_path(file_path, server_dir)
        if resolved_path and resolved_path.exists():
            try:
                with open(resolved_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                config = _deep_merge(config, file_config)
                logger.info(f"Loaded configuration from: {resolved_path}")
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Invalid YAML in config file: {e}")
            except IOError as e:
                raise ConfigurationError(f"Cannot read config file: {e}")
        else:
            # Explicit path provided but file doesn't exist
            logger.warning(f"Config file not found (using defaults): {file_path}")
    else:
        # Check for default config file (optional)
        default_config_path = server_dir / "pongogo-config.yaml"
        if default_config_path.exists():
            try:
                with open(default_config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                config = _deep_merge(config, file_config)
                logger.info(f"Loaded configuration from: {default_config_path}")
            except yaml.YAMLError as e:
                logger.warning(f"Invalid YAML in default config (ignoring): {e}")
            except IOError as e:
                logger.warning(f"Cannot read default config (ignoring): {e}")
        else:
            logger.debug("No config file found, using defaults")

    # Apply environment variable overrides
    knowledge_path_override = os.environ.get("PONGOGO_KNOWLEDGE_PATH")
    if knowledge_path_override:
        if "knowledge" not in config:
            config["knowledge"] = {}
        config["knowledge"]["path"] = knowledge_path_override
        logger.info(f"Knowledge path override from env: {knowledge_path_override}")

    # Resolve knowledge path
    if config.get("knowledge", {}).get("path"):
        resolved = _resolve_path(config["knowledge"]["path"], server_dir)
        config["knowledge"]["path"] = str(resolved) if resolved else None

    return config


def get_knowledge_path(config: Dict[str, Any], server_dir: Optional[Path] = None) -> Path:
    """
    Get knowledge base path from config or default.

    Args:
        config: Configuration dictionary from load_config()
        server_dir: Server directory for default path calculation

    Returns:
        Path to knowledge/instructions directory
    """
    if server_dir is None:
        server_dir = Path(__file__).parent

    path_str = config.get("knowledge", {}).get("path")
    if path_str:
        return Path(path_str)

    # Default: ../knowledge/instructions relative to server
    return (server_dir.parent / "knowledge" / "instructions").resolve()


def get_routing_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract routing configuration for create_router() factory.

    Args:
        config: Configuration dictionary from load_config()

    Returns:
        Dictionary suitable for passing to create_router()
    """
    routing = config.get("routing", {})
    return {
        "routing": {
            "engine": routing.get("engine"),
            "features": routing.get("features", {}),
        }
    }
