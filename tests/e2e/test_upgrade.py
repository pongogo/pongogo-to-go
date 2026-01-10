"""E2E tests for upgrade functionality.

Tests the complete upgrade flow:
1. Start with current stable release
2. Create data with that version
3. Upgrade to new version (current build)
4. Verify routing still works
5. Verify data preserved

These tests require Docker and network access to pull stable images.
"""

import contextlib
import shutil
import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Any

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


STABLE_IMAGE = "pongogo.azurecr.io/pongogo:stable"
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


def run_container_command(
    docker_client: Any,
    image: str,
    command: list[str],
    volumes: dict | None = None,
    environment: dict | None = None,
    timeout: int = 60,
) -> tuple[int, str]:
    """Run a one-shot command in a container and return exit code and logs.

    Returns:
        Tuple of (exit_code, logs)
    """
    container = docker_client.containers.run(
        image,
        detach=True,
        command=command,
        volumes=volumes or {},
        environment=environment or {},
    )

    try:
        # Wait for container to finish
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", -1)
        logs = container.logs().decode("utf-8")
        return exit_code, logs
    finally:
        with contextlib.suppress(Exception):
            container.remove(force=True)


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
        volumes = {str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"}}
        environment = {
            "PONGOGO_TEST_MODE": "1",
            "PONGOGO_KNOWLEDGE_PATH": "/app/.pongogo/instructions",
        }

        # Phase 1: Run stable version and verify routing works
        routing_code = """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.instruction_handler import InstructionHandler
from mcp_server.router import InstructionRouter

handler = InstructionHandler('/app/.pongogo/instructions')
handler.load_instructions()
router = InstructionRouter(handler)
result = router.route('how do I test?', limit=3)
print(f"ROUTE_SUCCESS: count={result.get('count', 0)}")
"""

        exit_code, logs = run_container_command(
            docker_client,
            STABLE_IMAGE,
            ["python", "-c", routing_code],
            volumes=volumes,
            environment=environment,
        )

        assert exit_code == 0, f"Stable routing failed (exit {exit_code}): {logs}"
        assert "ROUTE_SUCCESS" in logs, f"Stable routing failed: {logs}"

        # Phase 2: Run test (new) version and verify routing still works
        exit_code, logs = run_container_command(
            docker_client,
            TEST_IMAGE,
            ["python", "-c", routing_code],
            volumes=volumes,
            environment=environment,
        )

        assert exit_code == 0, f"Test routing failed (exit {exit_code}): {logs}"
        assert "ROUTE_SUCCESS" in logs, f"Test routing failed: {logs}"

    def test_upgrade_migrates_database_schema(
        self,
        docker_client: Any,
        stable_image_available: bool,
        test_image_available: bool,
        test_project: Path,
    ):
        """Database schema should migrate correctly during upgrade.

        Note: The current stable image doesn't have mcp_server.database module,
        so we create a 3.0.0 schema file directly and verify the new version
        migrates it correctly.
        """
        pongogo_dir = test_project / ".pongogo"
        db_path = pongogo_dir / "pongogo.db"

        # Create a 3.0.0 schema database directly (simulating stable version)
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE schema_info (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO schema_info (key, value) VALUES ('schema_version', '3.0.0');

            CREATE TABLE routing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                message_hash TEXT,
                routed_instructions TEXT,
                instruction_count INTEGER DEFAULT 0,
                routing_scores TEXT,
                engine_version TEXT DEFAULT 'durian-0.6.1',
                session_id TEXT,
                context TEXT,
                routing_latency_ms REAL,
                exclude_from_eval BOOLEAN DEFAULT 0,
                exclude_reason TEXT,
                mode TEXT NOT NULL DEFAULT 'enabled'
            );

            -- Insert test data
            INSERT INTO routing_events (timestamp, user_message, instruction_count, mode)
            VALUES ('2025-01-01T00:00:00', 'test upgrade message', 1, 'enabled');

            CREATE TABLE routing_triggers (
                id INTEGER PRIMARY KEY,
                trigger_type TEXT,
                trigger_key TEXT,
                trigger_value TEXT,
                source TEXT,
                enabled BOOLEAN DEFAULT 1
            );
            CREATE TABLE artifact_discovered (
                id INTEGER PRIMARY KEY,
                status TEXT,
                source_type TEXT
            );
            CREATE TABLE artifact_implemented (
                id INTEGER PRIMARY KEY,
                status TEXT,
                instruction_category TEXT
            );
            CREATE TABLE observation_discovered (
                id INTEGER PRIMARY KEY,
                status TEXT,
                observation_type TEXT
            );
            CREATE TABLE observation_implemented (
                id INTEGER PRIMARY KEY,
                status TEXT,
                implementation_type TEXT
            );
            CREATE TABLE scan_history (
                id INTEGER PRIMARY KEY,
                scan_date TEXT
            );
        """)
        conn.commit()
        conn.close()

        # Verify 3.0.0 schema was created
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT value FROM schema_info WHERE key='schema_version'"
        )
        version = cursor.fetchone()[0]
        conn.close()
        assert version == "3.0.0", f"Test setup failed: got version {version}"

        # Open with test version - should migrate to 3.1.0
        volumes = {str(pongogo_dir): {"bind": "/app/.pongogo", "mode": "rw"}}

        migration_code = """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.database import PongogoDatabase, SCHEMA_VERSION

db = PongogoDatabase(db_path='/app/.pongogo/pongogo.db')
version = db.get_schema_version()
print(f"SCHEMA_VERSION: {version}")
print(f"EXPECTED_VERSION: {SCHEMA_VERSION}")

# Verify data preserved
events = db.execute("SELECT user_message FROM routing_events")
if events and events[0]['user_message'] == 'test upgrade message':
    print("DATA_PRESERVED: yes")
else:
    print("DATA_PRESERVED: no")

# Verify new table exists
tables = db.execute("SELECT name FROM sqlite_master WHERE name='guidance_fulfillment'")
if tables:
    print("NEW_TABLE_EXISTS: yes")
else:
    print("NEW_TABLE_EXISTS: no")
"""

        exit_code, logs = run_container_command(
            docker_client,
            TEST_IMAGE,
            ["python", "-c", migration_code],
            volumes=volumes,
            environment={"PONGOGO_TEST_MODE": "1"},
        )

        assert exit_code == 0, f"Migration failed (exit {exit_code}): {logs}"
        assert "SCHEMA_VERSION: 3.1.0" in logs, f"Schema not upgraded: {logs}"
        assert "DATA_PRESERVED: yes" in logs, f"Data not preserved: {logs}"
        assert "NEW_TABLE_EXISTS: yes" in logs, f"New table not created: {logs}"


class TestUpgradeToolOutput:
    """Tests for upgrade_pongogo MCP tool output."""

    def test_upgrade_tool_returns_instructions(
        self,
        docker_client: Any,
        test_image_available: bool,
        tmp_path: Path,
    ):
        """upgrade_pongogo tool should return upgrade instructions."""
        upgrade_code = """
import sys
sys.path.insert(0, '/app/src')
from mcp_server.upgrade import upgrade

result = upgrade()
print(f"SUCCESS: {result.success}")
print(f"METHOD: {result.method.value}")
print(f"HAS_COMMAND: {result.upgrade_command is not None}")
if result.upgrade_command:
    print(f"COMMAND: {result.upgrade_command}")
"""

        exit_code, logs = run_container_command(
            docker_client,
            TEST_IMAGE,
            ["python", "-c", upgrade_code],
            environment={"PONGOGO_TEST_MODE": "1"},
        )

        assert exit_code == 0, f"Upgrade tool failed (exit {exit_code}): {logs}"
        assert "SUCCESS: True" in logs
        assert "METHOD: docker" in logs
        assert "HAS_COMMAND: True" in logs
        assert "docker pull" in logs
