"""The assistant's expense tools: a port (what the agent needs) and its MCP adapter (how it's done).

The agent only knows ExpenseTools. The composition root (main.py) decides what's behind it:
- by default, this app's own MCP server, called **in-process**: same tools, same protocol, no network
  hop and no request to our own HTTP port;
- with MCP_URL set, a remote MCP server over Streamable HTTP, sending MCP_TOKEN as a bearer token.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.types import Tool

from app.core.errors import ExternalServiceError
from app.core.llm import ToolSpec
from app.modules.mcp import ResourceUri

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Give up if the tools don't answer in this many seconds, rather than hang the chat.
TIMEOUT_SECONDS = 15


class ToolsUnavailableError(ExternalServiceError):
    """The expense tools couldn't be reached, or didn't answer in time."""


@dataclass(frozen=True)
class ToolOutput:
    text: str  # what the model reads: the result, or the error message
    ok: bool  # False: the tool ran and reported a problem (e.g. "Unknown category"), useful to the model
    data: dict[str, Any] | None = None  # the typed result (MCP structuredContent), for cards


class ExpenseTools(Protocol):
    def specs(self) -> list[ToolSpec]:
        """Every tool, described for the model."""
        ...

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutput: ...

    def changes_data(self, name: str) -> bool:
        """Whether a tool may change data, so the pages know to reload."""
        ...

    def category_names(self) -> list[str]: ...


class McpExpenseTools:
    """ExpenseTools over MCP, with any server the SDK's Client can reach."""

    def __init__(self, target: MCPServer | str, token: str | None = None) -> None:
        self._target = target
        self._token = token
        # Fetched on first use, then remembered for this app's lifetime (restart to pick up new tools).
        self._tools: list[Tool] | None = None

    async def _with_client(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        if isinstance(self._target, MCPServer):
            async with Client(self._target) as client:
                return await operation(client)
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else None
        async with httpx2.AsyncClient(headers=headers) as http:
            async with Client(streamable_http_client(self._target, http_client=http)) as client:
                return await operation(client)

    def _run(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        """Connect, do one thing, disconnect.

        The MCP SDK is async, but the agent runs in a plain worker thread (FastAPI runs sync routes
        there), so each operation gets its own short event loop.
        """
        try:
            return asyncio.run(asyncio.wait_for(self._with_client(operation), TIMEOUT_SECONDS))
        except Exception as exc:  # connection refused, timeout, protocol errors (often wrapped in an ExceptionGroup)
            where = "this app's MCP server" if isinstance(self._target, MCPServer) else self._target
            raise ToolsUnavailableError(f"Could not reach the expense tools ({where})") from exc

    def _list(self) -> list[Tool]:
        if self._tools is None:

            async def list_tools(client: Client) -> list[Tool]:
                return list((await client.list_tools()).tools)

            self._tools = self._run(list_tools)
        return self._tools

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(name=tool.name, description=tool.description or "", parameters=tool.input_schema or {})
            for tool in self._list()
        ]

    def changes_data(self, name: str) -> bool:
        # The MCP spec says to assume a tool without the hint may change things, so only tools the
        # server marks read-only count as safe. Answered from the cached list: no extra request.
        tool = next((tool for tool in self._list() if tool.name == name), None)
        annotations = tool.annotations if tool else None
        return not (annotations and annotations.read_only_hint)

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutput:
        async def call_tool(client: Client) -> ToolOutput:
            result = await client.call_tool(name, arguments)
            text = "".join(getattr(part, "text", "") for part in result.content)
            data = result.structured_content if isinstance(result.structured_content, dict) else None
            # is_error means the tool ran and reported a problem; that's useful to the model, so it's
            # returned rather than raised.
            return ToolOutput(text=text, ok=not result.is_error, data=None if result.is_error else data)

        return self._run(call_tool)

    def category_names(self) -> list[str]:
        async def read(client: Client) -> list[str]:
            result = await client.read_resource(ResourceUri.CATEGORIES)
            return [category["name"] for category in json.loads(getattr(result.contents[0], "text", "[]"))]

        return self._run(read)
