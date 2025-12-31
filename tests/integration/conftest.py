"""Integration test fixtures.

Re-exports fixtures from main conftest for integration tests.
"""

# Re-export fixtures from main conftest
from tests.conftest import (
    docker_client,
    fixtures_dir,
    mock_mcp_client,
    pongogo_server,
    pongogo_server_image,
    project_root,
    sample_instructions,
    server_port,
)

__all__ = [
    "docker_client",
    "fixtures_dir",
    "mock_mcp_client",
    "pongogo_server",
    "pongogo_server_image",
    "project_root",
    "sample_instructions",
    "server_port",
]
