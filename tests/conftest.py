"""Shared pytest fixtures for pongogo-to-go tests.

This module provides Docker container management fixtures for integration
and E2E tests. Unit tests run without Docker.
"""

import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Optional docker import - only needed for integration/E2E tests
try:
    import docker
    from docker.models.containers import Container

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    Container = Any  # type: ignore[misc,assignment]


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_project(fixtures_dir: Path) -> Path:
    """Return path to minimal (empty) project fixture."""
    return fixtures_dir / "minimal-project"


@pytest.fixture
def initialized_project(fixtures_dir: Path) -> Path:
    """Return path to initialized project fixture."""
    return fixtures_dir / "initialized-project"


@pytest.fixture
def sample_instructions(fixtures_dir: Path) -> Path:
    """Return path to sample instructions fixture."""
    return fixtures_dir / "sample-instructions"


# =============================================================================
# Docker Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def docker_client() -> Generator[Any, None, None]:
    """Provide Docker client for container management.

    Yields None if Docker is not available, allowing tests to skip gracefully.
    """
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker SDK not installed")
        return

    try:
        client = docker.from_env()
        # Quick connectivity check
        client.ping()
        yield client
    except docker.errors.DockerException as e:
        pytest.skip(f"Docker not available: {e}")


def _wait_for_container(container: Container, timeout: int = 30) -> None:
    """Wait for container to be running.

    Args:
        container: Docker container to wait for
        timeout: Maximum seconds to wait

    Raises:
        TimeoutError: If container doesn't start in time
    """
    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        if container.status == "running":
            return
        if container.status in ("exited", "dead"):
            logs = container.logs().decode("utf-8")
            raise RuntimeError(f"Container failed to start: {logs}")
        time.sleep(0.5)
    raise TimeoutError(f"Container did not start within {timeout}s")


@pytest.fixture(scope="session")
def pongogo_server_image(docker_client: Any) -> str:
    """Ensure pongogo-server test image is built.

    Returns the image tag to use for tests.
    """
    if docker_client is None:
        pytest.skip("Docker client not available")

    image_tag = "pongogo-server:test"
    project_root = Path(__file__).parent.parent

    # Check if image exists and is recent enough
    try:
        docker_client.images.get(image_tag)
    except docker.errors.ImageNotFound:
        # Build the image
        docker_client.images.build(
            path=str(project_root),
            dockerfile="Dockerfile",
            tag=image_tag,
            rm=True,
        )

    return image_tag


@pytest.fixture(scope="session")
def pongogo_server(
    docker_client: Any,
    pongogo_server_image: str,
) -> Generator[Container, None, None]:
    """Start Pongogo MCP server container for E2E tests.

    This fixture is session-scoped so the container is shared across all
    E2E tests for efficiency.
    """
    if docker_client is None:
        pytest.skip("Docker client not available")

    fixtures_path = Path(__file__).parent / "fixtures"

    container = docker_client.containers.run(
        pongogo_server_image,
        detach=True,
        environment={
            "PONGOGO_TEST_MODE": "1",
            "PONGOGO_KNOWLEDGE_PATH": "/app/tests/fixtures/sample-instructions",
        },
        volumes={
            str(fixtures_path): {
                "bind": "/app/tests/fixtures",
                "mode": "ro",
            }
        },
        ports={"8000/tcp": None},  # Random available port
    )

    try:
        _wait_for_container(container)
        yield container
    finally:
        container.stop()
        container.remove()


@pytest.fixture
def server_port(pongogo_server: Container) -> int:
    """Get the mapped port for the pongogo server."""
    pongogo_server.reload()
    port_info = pongogo_server.ports.get("8000/tcp")
    if port_info:
        return int(port_info[0]["HostPort"])
    raise RuntimeError("Server port not mapped")


# =============================================================================
# State Management Fixtures
# =============================================================================


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory for tests that modify files.

    This is preferred over using fixtures directly when tests need to
    write files, to avoid polluting fixtures.
    """
    project = tmp_path / "test-project"
    project.mkdir()
    return project


@pytest.fixture
def temp_pongogo_dir(temp_project: Path) -> Path:
    """Create a temporary .pongogo directory."""
    pongogo_dir = temp_project / ".pongogo"
    pongogo_dir.mkdir()
    return pongogo_dir
