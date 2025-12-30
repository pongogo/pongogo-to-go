"""E2E test fixtures.

Provides Docker container fixtures for full workflow testing.
Uses pytest-docker for container lifecycle management.
"""

# Re-export fixtures from main conftest
from tests.conftest import (
    docker_client,
    fixtures_dir,
    pongogo_server,
    pongogo_server_image,
    project_root,
    server_port,
)

__all__ = [
    "docker_client",
    "fixtures_dir",
    "pongogo_server",
    "pongogo_server_image",
    "project_root",
    "server_port",
]
