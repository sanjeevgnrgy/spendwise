"""The expense tools over MCP: McpExpenseTools, the adapter behind the ExpenseTools port (port.py).

Adapter. The agent only knows the port; the composition root (bootstrap.py) creates this adapter, through
module.py, and decides which server it reaches:
- by default, this app's own MCP server, called **in-process**: same tools, same protocol, no network
  hop and no request to our own HTTP port;
- with MCP_URL set, a remote MCP server over Streamable HTTP, sending MCP_TOKEN as a bearer token.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.types import Tool
from pydantic import BaseModel, TypeAdapter

from app.core.i18n import translatable
from app.core.llm import ToolSpec
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.tools.port import ToolOutput, ToolsUnavailableError
from app.modules.mcp import AUTHORIZATION_HEADER, BEARER_SCHEME, ResourceUri

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Give up if the tools don't answer in this many seconds, rather than hang the chat.
TIMEOUT_SECONDS = 15
# A resource read with no text (it shouldn't happen) counts as no categories.
EMPTY_LIST_JSON = "[]"
# How the log names the in-process server, which has no URL.
IN_PROCESS_SERVER = "this app's MCP server (in-process)"


# Just the part of a category the assistant reads from the categories resource: its name (the rest is ignored).
class _CategoryName(BaseModel):
    name: str


_CATEGORIES = TypeAdapter(list[_CategoryName])


class _Connector(Protocol):
    """How to reach an MCP server: open one client session, and name the server for the log."""

    def describe(self) -> str:
        """Which server this is, for the server log only: a person is never shown it (D180)."""
        ...

    def open(self) -> AbstractAsyncContextManager[Client]:
        """A connected client for one session, closed when the `async with` ends."""
        ...


@dataclass(frozen=True)
class _InProcess:
    """This app's own MCP server object, called directly: same protocol, no network."""

    server: MCPServer

    def describe(self) -> str:
        """The in-process server isn't at a URL, so it's named in words."""
        return IN_PROCESS_SERVER

    def open(self) -> AbstractAsyncContextManager[Client]:
        """A client connected straight to the server object."""
        return Client(self.server)


@dataclass(frozen=True)
class _Remote:
    """An MCP server at a URL, over Streamable HTTP, with an optional bearer token."""

    url: str
    token: str | None

    def describe(self) -> str:
        """The server's URL (never the token)."""
        return self.url

    @asynccontextmanager
    async def open(self) -> AsyncIterator[Client]:
        """A client over HTTP, sending the token (if any) with every request."""
        headers = {AUTHORIZATION_HEADER: f"{BEARER_SCHEME} {self.token}"} if self.token else None
        async with httpx2.AsyncClient(headers=headers) as http:
            async with Client(streamable_http_client(self.url, http_client=http)) as client:
                yield client


class McpExpenseTools:
    """ExpenseTools over MCP, with any server the SDK's Client can reach."""

    def __init__(self, target: MCPServer | str, token: str | None = None) -> None:
        """`target` is the server object (in-process) or a URL (remote, sent `token` as a bearer token)."""
        # The transport is picked once, here; everything below just opens a session with it.
        self._connector: _Connector = _InProcess(target) if isinstance(target, MCPServer) else _Remote(target, token)
        # Fetched on first use, then remembered for this app's lifetime (restart to pick up new tools).
        self._tools: list[Tool] | None = None

    async def _with_client(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        """Open a session, run `operation` with its client, and close the session. Returns its result."""
        async with self._connector.open() as client:
            return await operation(client)

    def _run(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        """Connect, do one thing, disconnect. Raises ToolsUnavailableError on any failure or timeout.

        The MCP SDK is async, but the agent runs in a plain worker thread (FastAPI runs sync routes
        there), so each operation gets its own short event loop.
        """
        try:
            return asyncio.run(asyncio.wait_for(self._with_client(operation), TIMEOUT_SECONDS))
        except Exception as exc:  # connection refused, timeout, protocol errors (often wrapped in an ExceptionGroup)
            # Which server, and why, are for the log; a person is told only that the tools can't be reached (D180).
            logger.warning("expense tools unreachable (%s): %r", self._connector.describe(), exc)
            raise ToolsUnavailableError(translatable(ChatText.TOOLS_UNREACHABLE)) from exc

    def _list(self) -> list[Tool]:
        """The server's tools, asked for once and then cached."""
        if self._tools is None:

            async def list_tools(client: Client) -> list[Tool]:
                """Every tool the server offers."""
                return list((await client.list_tools()).tools)

            self._tools = self._run(list_tools)
        return self._tools

    def specs(self) -> list[ToolSpec]:
        """Every tool, as the server describes it (name, description, input schema), in the server's order."""
        return [
            ToolSpec(name=tool.name, description=tool.description or "", parameters=tool.input_schema or {})
            for tool in self._list()
        ]

    def changes_data(self, name: str) -> bool:
        """Whether a tool may change data: True unless the server marks it read-only."""
        # The MCP spec says to assume a tool without the hint may change things, so only tools the
        # server marks read-only count as safe. Usually answered from the cached list, with no request.
        try:
            listed = self._list()
        except ToolsUnavailableError:
            # The list couldn't be fetched (a remote server, right after a restart, before any turn listed the
            # tools). This is asked after the tool has run, so raising would fail a turn whose change is already
            # saved: assume it may have changed data, as the spec says for any tool it can't vouch for.
            return True
        tool = next((tool for tool in listed if tool.name == name), None)
        annotations = tool.annotations if tool else None
        return not (annotations and annotations.read_only_hint)

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutput:
        """Run one tool on the server, in its own session. A tool's own error comes back as ok=False."""

        async def call_tool(client: Client) -> ToolOutput:
            """The call, with the result's text for the model and its structured content for cards."""
            result = await client.call_tool(name, arguments)
            text = "".join(getattr(part, "text", "") for part in result.content)
            data = result.structured_content if isinstance(result.structured_content, dict) else None
            # is_error means the tool ran and reported a problem; that's useful to the model, so it's
            # returned rather than raised.
            return ToolOutput(text=text, ok=not result.is_error, data=None if result.is_error else data)

        return self._run(call_tool)

    def category_names(self) -> list[str]:
        """The category names, read from the server's categories resource (fresh each turn)."""

        async def read(client: Client) -> list[str]:
            """Read the resource and keep each category's name."""
            result = await client.read_resource(ResourceUri.CATEGORIES)
            categories = _CATEGORIES.validate_json(getattr(result.contents[0], "text", EMPTY_LIST_JSON))
            return [category.name for category in categories]

        return self._run(read)
