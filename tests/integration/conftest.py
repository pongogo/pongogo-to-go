"""Integration test fixtures.

Provides fixtures for testing component interactions:
- Initialized project fixtures
- Server process management
- Workflow test helpers
"""

import os
import shutil
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def initialized_project(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Create a fully initialized pongogo project.

    Copies the initialized-project fixture to a temp directory
    for integration testing.
    """
    source = fixtures_dir / "initialized-project"
    dest = tmp_path / "project"

    if source.exists():
        shutil.copytree(source, dest)
    else:
        # Create minimal structure if fixture doesn't exist
        (dest / ".pongogo").mkdir(parents=True)
        (dest / ".pongogo" / "config.yaml").write_text("version: '1.0.0'\n")

    return dest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mcp_server_process(
    initialized_project: Path,
) -> Generator[subprocess.Popen, None, None]:
    """Start MCP server as subprocess for integration tests.

    Starts pongogo-server pointing to the initialized project
    with test mode enabled.
    """
    env = {
        **os.environ,
        "PONGOGO_TEST_MODE": "1",
        "PONGOGO_KNOWLEDGE_PATH": str(
            initialized_project / ".pongogo" / "instructions"
        ),
    }

    process = subprocess.Popen(
        ["pongogo-server"],
        cwd=str(initialized_project),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    yield process

    process.terminate()
    process.wait(timeout=5)
