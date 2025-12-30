# Mock MCP Client Specification

**Issue**: [#369](https://github.com/pongogo/pongogo/issues/369) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document specifies the Mock MCP Client - a test utility for invoking Pongogo MCP server tools programmatically without requiring Claude Code.

**Core Purpose**: Enable E2E and integration tests to validate server behavior through the same protocol Claude Code uses.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Test Execution                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐         ┌────────────────────────────────────┐  │
│  │    pytest          │         │    Docker Container                 │  │
│  │                    │         │                                     │  │
│  │  ┌──────────────┐  │  stdio  │  ┌──────────────────────────────┐  │  │
│  │  │ MockMCPClient│──┼─────────┼──│  pongogo-server (FastMCP)    │  │  │
│  │  │              │  │ JSON-RPC│  │                               │  │  │
│  │  │ call_tool()  │◀─┼─────────┼──│  route_instructions          │  │  │
│  │  │ list_tools() │  │         │  │  get_instructions            │  │  │
│  │  └──────────────┘  │         │  │  search_instructions         │  │  │
│  │                    │         │  │  switch_engine               │  │  │
│  │  ┌──────────────┐  │         │  │  ...                         │  │  │
│  │  │ Assertions   │  │         │  └──────────────────────────────┘  │  │
│  │  └──────────────┘  │         │                                     │  │
│  └────────────────────┘         └────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Protocol Essentials

### JSON-RPC 2.0 Message Format

MCP uses JSON-RPC 2.0 over stdio (stdin/stdout).

**Request Format**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "route_instructions",
    "arguments": {
      "message": "how do I conduct a retrospective?",
      "limit": 5
    }
  }
}
```

**Success Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "..."
      }
    ]
  }
}
```

**Error Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": { "details": "..." }
  }
}
```

### MCP Methods Used

| Method | Purpose |
|--------|---------|
| `initialize` | Establish connection, exchange capabilities |
| `tools/list` | Discover available tools |
| `tools/call` | Invoke a specific tool |

---

## MockMCPClient Class Design

### File Location

```
tests/
└── helpers/
    ├── __init__.py
    └── mock_mcp_client.py
```

### Class Interface

```python
# tests/helpers/mock_mcp_client.py
"""Mock MCP Client for testing Pongogo server."""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MCPResponse:
    """Parsed MCP response."""
    success: bool
    content: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_jsonrpc(cls, response: dict) -> "MCPResponse":
        """Parse JSON-RPC response into MCPResponse."""
        if "error" in response:
            return cls(
                success=False,
                error_code=response["error"].get("code"),
                error_message=response["error"].get("message"),
                raw=response
            )

        # Extract text content from MCP response format
        result = response.get("result", {})
        content_list = result.get("content", [])
        text_content = ""
        for item in content_list:
            if item.get("type") == "text":
                text_content += item.get("text", "")

        return cls(
            success=True,
            content=text_content,
            raw=response
        )


class MockMCPClient:
    """
    Mock MCP client for testing Pongogo server.

    Communicates with pongogo-server via JSON-RPC over stdio,
    mimicking Claude Code's MCP client behavior.
    """

    def __init__(
        self,
        server_command: list[str] | None = None,
        working_dir: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0
    ):
        """
        Initialize mock MCP client.

        Args:
            server_command: Command to start server (default: ["pongogo-server"])
            working_dir: Working directory for server process
            env: Environment variables for server process
            timeout: Default timeout for operations in seconds
        """
        self.server_command = server_command or ["pongogo-server"]
        self.working_dir = working_dir
        self.env = env or {}
        self.timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._initialized = False

    async def __aenter__(self) -> "MockMCPClient":
        """Async context manager entry - start server and initialize."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - stop server."""
        await self.stop()

    async def start(self) -> None:
        """Start the MCP server process."""
        import os

        env = {**os.environ, **self.env, "PONGOGO_TEST_MODE": "1"}

        self._process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.working_dir,
            env=env,
            text=True,
            bufsize=1  # Line buffered
        )

        # Initialize MCP connection
        await self._initialize()

    async def stop(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            self._initialized = False

    async def _initialize(self) -> dict:
        """
        Send MCP initialize request.

        Establishes the MCP connection and exchanges capabilities.
        """
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "MockMCPClient",
                "version": "1.0.0"
            }
        })
        self._initialized = True
        return response

    async def list_tools(self) -> list[dict]:
        """
        List available tools from the server.

        Returns:
            List of tool definitions with name, description, inputSchema
        """
        response = await self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None
    ) -> MCPResponse:
        """
        Call an MCP tool.

        Args:
            name: Tool name (e.g., "route_instructions")
            arguments: Tool arguments as dict

        Returns:
            MCPResponse with parsed result or error
        """
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
        return MCPResponse.from_jsonrpc(response)

    async def _send_request(self, method: str, params: dict) -> dict:
        """
        Send JSON-RPC request and receive response.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Parsed JSON-RPC response

        Raises:
            TimeoutError: If no response within timeout
            RuntimeError: If server process not running
        """
        if not self._process or self._process.poll() is not None:
            raise RuntimeError("MCP server process not running")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }

        # Send request
        request_line = json.dumps(request) + "\n"
        self._process.stdin.write(request_line)
        self._process.stdin.flush()

        # Read response with timeout
        loop = asyncio.get_event_loop()
        try:
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, self._process.stdout.readline),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response within {self.timeout}s")

        if not response_line:
            stderr = self._process.stderr.read()
            raise RuntimeError(f"Server closed connection. stderr: {stderr}")

        return json.loads(response_line)

    # =========================================================================
    # Convenience Methods for Common Tools
    # =========================================================================

    async def route_instructions(
        self,
        message: str,
        context: dict | None = None,
        limit: int = 5
    ) -> MCPResponse:
        """
        Route a message to get relevant instructions.

        This is the primary tool for instruction routing.

        Args:
            message: User message to route
            context: Optional conversation context
            limit: Maximum instructions to return

        Returns:
            MCPResponse with routed instructions
        """
        return await self.call_tool("route_instructions", {
            "message": message,
            "context": context,
            "limit": limit
        })

    async def get_instructions(
        self,
        topic: str | None = None,
        category: str | None = None,
        exact_match: bool = False
    ) -> MCPResponse:
        """
        Get instructions by topic or category filter.

        Args:
            topic: Filter by topic
            category: Filter by category
            exact_match: Require exact match

        Returns:
            MCPResponse with matching instructions
        """
        args = {}
        if topic:
            args["topic"] = topic
        if category:
            args["category"] = category
        args["exact_match"] = exact_match

        return await self.call_tool("get_instructions", args)

    async def search_instructions(
        self,
        query: str,
        limit: int = 10
    ) -> MCPResponse:
        """
        Full-text search across instructions.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            MCPResponse with search results
        """
        return await self.call_tool("search_instructions", {
            "query": query,
            "limit": limit
        })

    async def switch_engine(self, engine_version: str) -> MCPResponse:
        """
        Switch routing engine version.

        Args:
            engine_version: Engine version (e.g., "durian-0.6")

        Returns:
            MCPResponse with switch confirmation
        """
        return await self.call_tool("switch_engine", {
            "engine_version": engine_version
        })
```

---

## Pytest Fixtures

### File Location

```
tests/
├── conftest.py           # Root conftest imports from helpers
└── e2e/
    └── conftest.py       # E2E-specific fixtures
```

### Fixture Implementations

```python
# tests/conftest.py
"""Shared pytest fixtures for pongogo-to-go tests."""

import pytest
from pathlib import Path

# Make helpers importable
pytest_plugins = ["tests.helpers"]


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_instructions_dir(fixtures_dir) -> Path:
    """Path to sample instructions for testing."""
    return fixtures_dir / "sample-instructions"


@pytest.fixture(scope="session")
def initialized_project_dir(fixtures_dir) -> Path:
    """Path to initialized project fixture."""
    return fixtures_dir / "initialized-project"
```

```python
# tests/e2e/conftest.py
"""E2E test fixtures with Docker container management."""

import pytest
import docker
from pathlib import Path
from typing import Generator

from tests.helpers.mock_mcp_client import MockMCPClient


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Provide Docker client for container management."""
    return docker.from_env()


@pytest.fixture(scope="session")
def pongogo_image(docker_client) -> str:
    """
    Build and return pongogo-server test image.

    Image is built once per test session.
    """
    image_tag = "pongogo-server:test"

    # Build from project root
    project_root = Path(__file__).parent.parent.parent

    docker_client.images.build(
        path=str(project_root),
        dockerfile="tests/Dockerfile",
        tag=image_tag,
        target="test",
        rm=True
    )

    return image_tag


@pytest.fixture(scope="function")
async def mock_mcp_client(
    tmp_path: Path,
    sample_instructions_dir: Path
) -> Generator[MockMCPClient, None, None]:
    """
    Provide MockMCPClient connected to pongogo-server.

    Server runs as subprocess (not Docker) for faster tests.
    Use `mock_mcp_client_docker` for full Docker isolation.
    """
    import shutil

    # Create test project structure
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    pongogo_dir = project_dir / ".pongogo"
    pongogo_dir.mkdir()

    # Copy sample instructions
    shutil.copytree(
        sample_instructions_dir,
        pongogo_dir / "instructions"
    )

    # Create mock MCP client
    client = MockMCPClient(
        server_command=["pongogo-server"],
        working_dir=project_dir,
        env={
            "PONGOGO_KNOWLEDGE_PATH": str(pongogo_dir / "instructions"),
            "PONGOGO_TEST_MODE": "1"
        },
        timeout=30.0
    )

    async with client:
        yield client


@pytest.fixture(scope="session")
def pongogo_container(
    docker_client,
    pongogo_image: str,
    fixtures_dir: Path
) -> Generator[docker.models.containers.Container, None, None]:
    """
    Start pongogo-server in Docker container for E2E tests.

    Container runs for entire test session for efficiency.
    """
    container = docker_client.containers.run(
        pongogo_image,
        detach=True,
        stdin_open=True,  # Keep stdin open for MCP communication
        environment={
            "PONGOGO_TEST_MODE": "1",
            "PONGOGO_LOG_LEVEL": "DEBUG"
        },
        volumes={
            str(fixtures_dir / "sample-instructions"): {
                "bind": "/app/tests/fixtures/sample-instructions",
                "mode": "ro"
            }
        }
    )

    # Wait for container to be ready
    _wait_for_container_ready(container, timeout=30)

    yield container

    # Cleanup
    container.stop(timeout=5)
    container.remove(force=True)


def _wait_for_container_ready(container, timeout: int = 30) -> None:
    """Wait for container to reach running state."""
    import time

    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        if container.status == "running":
            # Additional health check could go here
            return
        time.sleep(0.5)

    raise TimeoutError(f"Container not ready within {timeout}s")


@pytest.fixture(scope="function")
async def mock_mcp_client_docker(
    pongogo_container
) -> Generator[MockMCPClient, None, None]:
    """
    MockMCPClient that communicates with Docker container.

    Uses `docker exec` to attach to container's stdio.
    """
    # Implementation for Docker-based communication
    # This is more complex and uses docker exec with attached stdio

    client = DockerMCPClient(container=pongogo_container)
    async with client:
        yield client
```

---

## Test Helper Utilities

### Assertion Helpers

```python
# tests/helpers/assertions.py
"""Assertion helpers for MCP response validation."""

from .mock_mcp_client import MCPResponse


def assert_routing_success(response: MCPResponse) -> None:
    """Assert that routing returned valid instructions."""
    assert response.success, f"Routing failed: {response.error_message}"
    assert response.content, "No content in response"
    assert len(response.content) > 0, "Empty content in response"


def assert_contains_instruction(
    response: MCPResponse,
    instruction_name: str
) -> None:
    """Assert response contains a specific instruction."""
    assert response.success, f"Request failed: {response.error_message}"
    assert instruction_name in response.content, \
        f"Expected '{instruction_name}' in response"


def assert_error_code(
    response: MCPResponse,
    expected_code: int
) -> None:
    """Assert response has specific error code."""
    assert not response.success, "Expected error response"
    assert response.error_code == expected_code, \
        f"Expected error code {expected_code}, got {response.error_code}"


def assert_tool_exists(tools: list[dict], tool_name: str) -> None:
    """Assert tool exists in tools list."""
    tool_names = [t["name"] for t in tools]
    assert tool_name in tool_names, \
        f"Tool '{tool_name}' not found. Available: {tool_names}"
```

### Response Matchers

```python
# tests/helpers/matchers.py
"""Response matchers for flexible assertions."""

import re
from dataclasses import dataclass
from typing import Pattern

from .mock_mcp_client import MCPResponse


@dataclass
class ContentMatcher:
    """Matcher for MCP response content."""

    patterns: list[Pattern | str]
    case_sensitive: bool = False

    def matches(self, response: MCPResponse) -> bool:
        """Check if response content matches all patterns."""
        if not response.success or not response.content:
            return False

        content = response.content
        if not self.case_sensitive:
            content = content.lower()

        for pattern in self.patterns:
            if isinstance(pattern, str):
                check = pattern if self.case_sensitive else pattern.lower()
                if check not in content:
                    return False
            else:
                if not pattern.search(content):
                    return False

        return True

    def assert_matches(self, response: MCPResponse) -> None:
        """Assert response matches, with helpful error message."""
        assert response.success, f"Response failed: {response.error_message}"
        assert response.content, "No content in response"

        content = response.content
        if not self.case_sensitive:
            content = content.lower()

        for pattern in self.patterns:
            if isinstance(pattern, str):
                check = pattern if self.case_sensitive else pattern.lower()
                assert check in content, \
                    f"Expected '{pattern}' in content. Got: {response.content[:200]}..."
            else:
                assert pattern.search(content), \
                    f"Pattern {pattern.pattern} not found in content"


# Pre-built matchers for common scenarios
LEARNING_LOOP_MATCHER = ContentMatcher(
    patterns=["learning loop", "retrospective"],
    case_sensitive=False
)

WORK_LOG_MATCHER = ContentMatcher(
    patterns=["work log", "entry"],
    case_sensitive=False
)

CHECKLIST_MATCHER = ContentMatcher(
    patterns=["checklist"],
    case_sensitive=False
)
```

---

## Usage Examples

### Basic Tool Invocation

```python
# tests/e2e/test_basic_routing.py
"""Basic routing tests."""

import pytest
from tests.helpers.assertions import assert_routing_success


@pytest.mark.asyncio
async def test_route_instructions_basic(mock_mcp_client):
    """Test basic instruction routing."""
    response = await mock_mcp_client.route_instructions(
        message="how do I conduct a retrospective?"
    )

    assert_routing_success(response)
    assert "retrospective" in response.content.lower()


@pytest.mark.asyncio
async def test_list_tools(mock_mcp_client):
    """Test tool discovery."""
    tools = await mock_mcp_client.list_tools()

    expected_tools = [
        "route_instructions",
        "get_instructions",
        "search_instructions"
    ]

    tool_names = [t["name"] for t in tools]
    for expected in expected_tools:
        assert expected in tool_names
```

### E2E Scenario Tests

```python
# tests/e2e/test_learning_loop.py
"""Learning loop E2E tests."""

import pytest
from tests.helpers.matchers import LEARNING_LOOP_MATCHER


@pytest.mark.asyncio
async def test_implicit_learning_loop_trigger(mock_mcp_client):
    """
    Test: User says "I'm done" → learning loop suggested.

    This validates the Recognize → Increment → Artifact flow
    for implicit learning loop triggers.
    """
    # Simulate completing some work
    await mock_mcp_client.route_instructions(
        message="I just finished implementing the new feature"
    )

    # Trigger with completion phrase
    response = await mock_mcp_client.route_instructions(
        message="I'm done with this task"
    )

    LEARNING_LOOP_MATCHER.assert_matches(response)


@pytest.mark.asyncio
async def test_explicit_retro_command(mock_mcp_client):
    """Test /pongogo-retro command produces retrospective."""
    response = await mock_mcp_client.route_instructions(
        message="/pongogo-retro"
    )

    assert response.success
    assert "what went well" in response.content.lower()
    assert "what could improve" in response.content.lower()
```

### Error Handling Tests

```python
# tests/e2e/test_error_handling.py
"""Error handling tests."""

import pytest
from tests.helpers.assertions import assert_error_code


@pytest.mark.asyncio
async def test_invalid_tool_name(mock_mcp_client):
    """Test calling non-existent tool."""
    response = await mock_mcp_client.call_tool(
        "nonexistent_tool",
        {"arg": "value"}
    )

    assert not response.success
    # MCP error code for method not found: -32601


@pytest.mark.asyncio
async def test_invalid_arguments(mock_mcp_client):
    """Test calling tool with invalid arguments."""
    response = await mock_mcp_client.call_tool(
        "route_instructions",
        {"invalid_param": 123}  # Missing required 'message'
    )

    assert not response.success
```

---

## Performance Considerations

### Test Speed Optimization

| Optimization | Approach |
|--------------|----------|
| Subprocess vs Docker | Use subprocess for integration tests (faster startup) |
| Session-scoped fixtures | Reuse server process across tests where safe |
| Parallel execution | Tests are isolated, support `pytest-xdist` |

### Recommended Fixture Scopes

| Fixture | Scope | Rationale |
|---------|-------|-----------|
| `mock_mcp_client` | function | Clean state per test |
| `pongogo_container` | session | Docker startup is slow |
| `docker_client` | session | Reuse connection |
| `fixtures_dir` | session | Static, never changes |

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `tests/helpers/` directory
- [ ] Implement `MockMCPClient` class in `mock_mcp_client.py`
- [ ] Implement `MCPResponse` dataclass
- [ ] Create assertion helpers in `assertions.py`
- [ ] Create response matchers in `matchers.py`
- [ ] Add pytest fixtures to `tests/conftest.py`
- [ ] Add E2E fixtures to `tests/e2e/conftest.py`
- [ ] Write basic routing tests as validation
- [ ] Document usage patterns

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Docker Environment: `docs/design/docker_test_environment.md`
- Test Pyramid: `docs/design/test_pyramid_layers.md`
- MCP Specification: https://modelcontextprotocol.io/specification
- FastMCP: https://github.com/jlowin/fastmcp
