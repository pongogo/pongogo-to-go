"""Mock MCP Client for testing Pongogo server.

This module provides a programmatic MCP client that communicates with
pongogo-server via JSON-RPC over stdio, mimicking Claude Code's behavior.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class MCPResponse:
    """Parsed MCP response."""

    success: bool
    content: str | None = None
    error_code: int | None = None
    error_message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_jsonrpc(cls, response: dict[str, Any]) -> MCPResponse:
        """Parse JSON-RPC response into MCPResponse.

        Args:
            response: Raw JSON-RPC response dict

        Returns:
            Parsed MCPResponse
        """
        if "error" in response:
            return cls(
                success=False,
                error_code=response["error"].get("code"),
                error_message=response["error"].get("message"),
                raw=response,
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
            raw=response,
        )


class MockMCPClient:
    """Mock MCP client for testing Pongogo server.

    Communicates with pongogo-server via JSON-RPC over stdio,
    mimicking Claude Code's MCP client behavior.

    Usage:
        async with MockMCPClient() as client:
            response = await client.route_instructions("how to do X?")
            assert response.success

    Attributes:
        server_command: Command to start the server
        working_dir: Working directory for server process
        env: Environment variables for server process
        timeout: Default timeout for operations in seconds
    """

    def __init__(
        self,
        server_command: list[str] | None = None,
        working_dir: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize mock MCP client.

        Args:
            server_command: Command to start server (default: ["pongogo-server"])
            working_dir: Working directory for server process
            env: Environment variables for server process
            timeout: Default timeout for operations in seconds
        """
        self.server_command = server_command or ["pongogo-server"]
        self.working_dir = working_dir
        self.env: dict[str, str] = dict(env) if env else {}
        self.timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._request_id = 0
        self._initialized = False

    async def __aenter__(self) -> MockMCPClient:
        """Async context manager entry - start server and initialize."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - stop server."""
        await self.stop()

    async def start(self) -> None:
        """Start the MCP server process."""
        env = {**os.environ, **self.env, "PONGOGO_TEST_MODE": "1"}

        self._process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.working_dir,
            env=env,
            text=True,
            bufsize=1,  # Line buffered
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

    async def _initialize(self) -> dict[str, Any]:
        """Send MCP initialize request.

        Establishes the MCP connection and exchanges capabilities.

        Returns:
            Initialize response from server
        """
        response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "MockMCPClient", "version": "1.0.0"},
            },
        )
        self._initialized = True

        # Send initialized notification (required by MCP protocol)
        await self._send_notification("notifications/initialized", {})

        return response

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server.

        Returns:
            List of tool definitions with name, description, inputSchema
        """
        response = await self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPResponse:
        """Call an MCP tool.

        Args:
            name: Tool name (e.g., "route_instructions")
            arguments: Tool arguments as dict

        Returns:
            MCPResponse with parsed result or error
        """
        response = await self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        return MCPResponse.from_jsonrpc(response)

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send JSON-RPC request and receive response.

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

        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("MCP server stdin/stdout not available")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
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
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response within {self.timeout}s") from None

        if not response_line:
            stderr_output = ""
            if self._process.stderr:
                stderr_output = self._process.stderr.read()
            raise RuntimeError(f"Server closed connection. stderr: {stderr_output}")

        return json.loads(response_line)

    async def _send_notification(
        self,
        method: str,
        params: dict[str, Any],
    ) -> None:
        """Send JSON-RPC notification (no response expected).

        Args:
            method: JSON-RPC method name
            params: Method parameters
        """
        if not self._process or self._process.poll() is not None:
            raise RuntimeError("MCP server process not running")

        if self._process.stdin is None:
            raise RuntimeError("MCP server stdin not available")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        # Send notification (no id = no response expected)
        notification_line = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_line)
        self._process.stdin.flush()

    # =========================================================================
    # Convenience Methods for Common Tools
    # =========================================================================

    async def route_instructions(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> MCPResponse:
        """Route a message to get relevant instructions.

        This is the primary tool for instruction routing.

        Args:
            message: User message to route
            context: Optional conversation context
            limit: Maximum instructions to return

        Returns:
            MCPResponse with routed instructions
        """
        args: dict[str, Any] = {"message": message, "limit": limit}
        if context:
            args["context"] = context
        return await self.call_tool("route_instructions", args)

    async def get_instructions(
        self,
        topic: str | None = None,
        category: str | None = None,
        exact_match: bool = False,
    ) -> MCPResponse:
        """Get instructions by topic or category filter.

        Args:
            topic: Filter by topic
            category: Filter by category
            exact_match: Require exact match

        Returns:
            MCPResponse with matching instructions
        """
        args: dict[str, Any] = {"exact_match": exact_match}
        if topic:
            args["topic"] = topic
        if category:
            args["category"] = category

        return await self.call_tool("get_instructions", args)

    async def search_instructions(
        self,
        query: str,
        limit: int = 10,
    ) -> MCPResponse:
        """Full-text search across instructions.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            MCPResponse with search results
        """
        return await self.call_tool(
            "search_instructions",
            {"query": query, "limit": limit},
        )

    async def switch_engine(self, engine_version: str) -> MCPResponse:
        """Switch routing engine version.

        Args:
            engine_version: Engine version (e.g., "durian-0.6")

        Returns:
            MCPResponse with switch confirmation
        """
        return await self.call_tool(
            "switch_engine",
            {"engine_version": engine_version},
        )
