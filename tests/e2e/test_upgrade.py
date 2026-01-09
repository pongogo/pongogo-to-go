"""E2E tests for upgrade functionality.

Tests the complete upgrade flow:
1. Start with current stable release
2. Create data with that version
3. Upgrade to new version (current build)
4. Verify routing still works
5. Verify data preserved

These tests require Docker and network access to pull stable images.
"""

import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Generator

import pytest

# Mark all tests as E2E and requiring Docker
pytestmark = [pytest.mark.e2e, pytest.mark.upgrade]

# Skip if Docker not available
try:
    import docker
    from docker.models.containers import Container

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    Container = Any


STABLE_IMAGE = "ghcr.io/pongogo/pongogo-to-go:stable"
TEST_IMAGE = "pongogo-server:test"


@pytest.fixture(scope="module")
def docker_client() -> Generator[Any, None, None]:
    """Provide Docker client for upgrade tests."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker SDK not installed")

    try:
        client = docker.from_env()
        client.ping()
        yield client
    except docker.errors.DockerException as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.fixture(scope="module")
def stable_image_available(docker_client: Any) -> bool:
    """Check if stable image is available, pull if not."""
    try:
        docker_client.images.get(STABLE_IMAGE)
        return True
    except docker.errors.ImageNotFound:
        try:
            print(f"Pulling {STABLE_IMAGE}...")
            docker_client.images.pull(STABLE_IMAGE)
            return True
        except docker.errors.APIError as e:
            pytest.skip(f"Could not pull stable image: {e}")
            return False


@pytest.fixture(scope="module")
def test_image_available(docker_client: Any) -> bool:
    """Check if test image (current build) is available."""
    try:
        docker_client.images.get(TEST_IMAGE)
        return True
    except docker.errors.ImageNotFound:
        # Build it
        project_root = Path(__file__).parent.parent.parent
        print(f"Building {TEST_IMAGE}...")
        docker_client.images.build(
            path=str(project_root),
            dockerfile="Dockerfile",
            tag=TEST_IMAGE,
            rm=True,
        )
        return True


def wait_for_container(container: Container, timeout: int = 30) -> None:
    """Wait for container to be running."""
    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        if container.status == "running":
            return
        if container.status in ("exited", "dead"):
            logs = container.logs().decode("utf-8")
            raise RuntimeError(f"Container failed: {logs}")
        time.sleep(0.5)
    raise TimeoutError(f"Container did not start within {timeout}s")


class TestUpgradeFlow:
    """Tests for complete upgrade flow."""

    @pytest.fixture
    def test_project(self, tmp_path: Path) -> Path:
        """Create a test project with sample instructions."""
        project = tmp_path / "upgrade-test-project"
        project.mkdir()

        pongogo_dir = project / ".pongogo"
        pongogo_dir.mkdir()

        # Copy sample instructions from fixtures
        fixtures = Path(__file__).parent.parent / "fixtures" / "sample-instructions"
        if fixtures.exists():
            shutil.copytree(fixtures, pongogo_dir / "instructions")
        else:
            # Create minimal instruction
            instr_dir = pongogo_dir / "instructions"
            instr_dir.mkdir()
            (instr_dir / "test.instructions.md").write_text(
                "# Test Instruction\nTest content for routing."
            )

        return project

    def test_upgrade_preserves_routing_functionality(
        self,
        docker_client: Any,
        stable_image_available: bool,
        test_image_available: bool,
        test_project: Path,
    ):
        """Routing should work before and after upgrade."""
        pongogo_dir = test_project / ".pongogo"

        # Phase 1: Run stable version and verify routing works
        stable_container = docker_client.containers.run(
            STABLE_IMAGE,
            detach=True,
            environment={
                "PONGOGO_TEST_MODE": "1",
                "PONGOGO_KNOWLEDGE_PATH": "/app/.pongogo/instructions",
            },
            volumes={
                str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"},
            },
            command=["python", "-c", """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.instruction_handler import InstructionHandler
from mcp_server.router import InstructionRouter

handler = InstructionHandler('/app/.pongogo/instructions')
handler.load_instructions()
router = InstructionRouter(handler)
result = router.route('how do I test?', limit=3)
print(f"STABLE_ROUTE_SUCCESS: count={result.get('count', 0)}")
"""],
        )

        try:
            wait_for_container(stable_container)
            time.sleep(2)  # Allow command to complete
            stable_container.reload()

            stable_logs = stable_container.logs().decode("utf-8")
            assert "STABLE_ROUTE_SUCCESS" in stable_logs, f"Stable routing failed: {stable_logs}"
        finally:
            stable_container.stop()
            stable_container.remove()

        # Phase 2: Run test (new) version and verify routing still works
        test_container = docker_client.containers.run(
            TEST_IMAGE,
            detach=True,
            environment={
                "PONGOGO_TEST_MODE": "1",
                "PONGOGO_KNOWLEDGE_PATH": "/app/.pongogo/instructions",
            },
            volumes={
                str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"},
            },
            command=["python", "-c", """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.instruction_handler import InstructionHandler
from mcp_server.router import InstructionRouter

handler = InstructionHandler('/app/.pongogo/instructions')
handler.load_instructions()
router = InstructionRouter(handler)
result = router.route('how do I test?', limit=3)
print(f"TEST_ROUTE_SUCCESS: count={result.get('count', 0)}")
"""],
        )

        try:
            wait_for_container(test_container)
            time.sleep(2)
            test_container.reload()

            test_logs = test_container.logs().decode("utf-8")
            assert "TEST_ROUTE_SUCCESS" in test_logs, f"Test routing failed: {test_logs}"
        finally:
            test_container.stop()
            test_container.remove()

    def test_upgrade_migrates_database_schema(
        self,
        docker_client: Any,
        stable_image_available: bool,
        test_image_available: bool,
        test_project: Path,
    ):
        """Database schema should migrate correctly during upgrade."""
        pongogo_dir = test_project / ".pongogo"

        # Phase 1: Create database with stable version
        stable_container = docker_client.containers.run(
            STABLE_IMAGE,
            detach=True,
            environment={"PONGOGO_TEST_MODE": "1"},
            volumes={
                str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"},
            },
            command=["python", "-c", """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.database import PongogoDatabase

db = PongogoDatabase(db_path='/app/.pongogo/pongogo.db')
version = db.get_schema_version()
print(f"STABLE_SCHEMA_VERSION: {version}")

# Insert test data
db.execute_insert('''
    INSERT INTO routing_events (timestamp, user_message, instruction_count)
    VALUES ('2025-01-01', 'test upgrade', 1)
''')
print("STABLE_DATA_INSERTED")
"""],
        )

        try:
            wait_for_container(stable_container)
            time.sleep(3)
            stable_container.reload()
            stable_logs = stable_container.logs().decode("utf-8")
            assert "STABLE_SCHEMA_VERSION" in stable_logs
            assert "STABLE_DATA_INSERTED" in stable_logs
        finally:
            stable_container.stop()
            stable_container.remove()

        # Phase 2: Open with test version - should migrate
        test_container = docker_client.containers.run(
            TEST_IMAGE,
            detach=True,
            environment={"PONGOGO_TEST_MODE": "1"},
            volumes={
                str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"},
            },
            command=["python", "-c", """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.database import PongogoDatabase, SCHEMA_VERSION

db = PongogoDatabase(db_path='/app/.pongogo/pongogo.db')
version = db.get_schema_version()
print(f"TEST_SCHEMA_VERSION: {version}")
print(f"EXPECTED_VERSION: {SCHEMA_VERSION}")

# Verify data preserved
events = db.execute("SELECT user_message FROM routing_events")
if events and events[0]['user_message'] == 'test upgrade':
    print("DATA_PRESERVED: yes")
else:
    print("DATA_PRESERVED: no")

# Verify new table exists
tables = db.execute("SELECT name FROM sqlite_master WHERE name='guidance_fulfillment'")
if tables:
    print("NEW_TABLE_EXISTS: yes")
else:
    print("NEW_TABLE_EXISTS: no")
"""],
        )

        try:
            wait_for_container(test_container)
            time.sleep(3)
            test_container.reload()
            test_logs = test_container.logs().decode("utf-8")

            assert "TEST_SCHEMA_VERSION: 3.1.0" in test_logs, f"Schema not upgraded: {test_logs}"
            assert "DATA_PRESERVED: yes" in test_logs, f"Data not preserved: {test_logs}"
            assert "NEW_TABLE_EXISTS: yes" in test_logs, f"New table not created: {test_logs}"
        finally:
            test_container.stop()
            test_container.remove()


class TestUpgradeToolOutput:
    """Tests for upgrade_pongogo MCP tool output."""

    def test_upgrade_tool_returns_instructions(
        self,
        docker_client: Any,
        test_image_available: bool,
        tmp_path: Path,
    ):
        """upgrade_pongogo tool should return upgrade instructions."""
        container = docker_client.containers.run(
            TEST_IMAGE,
            detach=True,
            environment={"PONGOGO_TEST_MODE": "1"},
            command=["python", "-c", """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.upgrade import upgrade

result = upgrade()
print(f"SUCCESS: {result.success}")
print(f"METHOD: {result.method.value}")
print(f"HAS_COMMAND: {result.upgrade_command is not None}")
if result.upgrade_command:
    print(f"COMMAND: {result.upgrade_command}")
"""],
        )

        try:
            wait_for_container(container)
            time.sleep(2)
            container.reload()
            logs = container.logs().decode("utf-8")

            assert "SUCCESS: True" in logs
            assert "METHOD: docker" in logs
            assert "HAS_COMMAND: True" in logs
            assert "docker pull" in logs
        finally:
            container.stop()
            container.remove()
