"""The expense tools over MCP: McpExpenseTools, the adapter behind the ExpenseTools port (port.py).

Adapter. The agent only knows the port; the composition root (bootstrap.py) creates this adapter, through
module.py, around this app's own MCP server, called **in-process**: same tools, same protocol, no network hop and
no request to our own HTTP port.

Every tool call is made for one person. The use cases bind the adapter to the signed-in person (acting_for), and
each call sets the MCP server's caller to them (mcp's acting_for, caller.py), so the tools read and change only that
person's expenses, whatever the model asks for (D191). An unbound adapter refuses to run a tool. (A remote MCP
server, MCP_URL, was dropped in Phase 23: it couldn't know who is signed in here.)
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import Tool
from pydantic import BaseModel, TypeAdapter

from app.core.i18n import translatable
from app.core.llm import ToolSpec
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.tools.port import ToolOutput, ToolsUnavailableError
from app.modules.mcp import ResourceUri
from app.modules.mcp import acting_for as serving_caller

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Give up if the tools don't answer in this many seconds, rather than hang the chat.
TIMEOUT_SECONDS = 15
# A resource read with no text (it shouldn't happen) counts as no categories.
EMPTY_LIST_JSON = "[]"
# How the log names the server, which has no URL.
IN_PROCESS_SERVER = "this app's MCP server (in-process)"
# A programming error, never shown to people (D180): a use case forgot to bind the tools to the signed-in person.
UNBOUND = "The expense tools were called without acting for anyone (use acting_for first)."


# Just the part of a category the assistant reads from the categories resource: its name (the rest is ignored).
class _CategoryName(BaseModel):
    name: str


_CATEGORIES = TypeAdapter(list[_CategoryName])


@dataclass
class _ToolList:
    """The server's tools, fetched on first use and then shared by every bound copy for the app's lifetime (restart
    to pick up new tools)."""

    tools: list[Tool] | None = None


class McpExpenseTools:
    """ExpenseTools over this app's own MCP server, in-process, acting for one person once bound (acting_for)."""

    def __init__(self, server: MCPServer, owner_id: int | None = None, listed: _ToolList | None = None) -> None:
        """`server` is the MCP server object; `owner_id` the person the tools act for (None until bound: no tool can
        run then). `listed` is the tool list shared with the copy this one was bound from."""
        self._server = server
        self._owner_id = owner_id
        self._listed = _ToolList() if listed is None else listed

    def acting_for(self, owner_id: int) -> McpExpenseTools:
        """A copy acting for `owner_id`: every tool call reads and changes only their expenses."""
        return McpExpenseTools(self._server, owner_id, self._listed)

    async def _with_client(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        """Open a session as the bound person (if any), run `operation` with its client, and close the session.

        The caller is set before the client connects: the server's tasks start inside, copy it, and so serve this
        session for that person only.
        """
        with ExitStack() as stack:
            if self._owner_id is not None:
                stack.enter_context(serving_caller(self._owner_id))
            async with Client(self._server) as client:
                return await operation(client)

    def _run(self, operation: Callable[[Client], Awaitable[T]]) -> T:
        """Connect, do one thing, disconnect. Raises ToolsUnavailableError on any failure or timeout.

        The MCP SDK is async, but the agent runs in a plain worker thread (FastAPI runs sync routes
        there), so each operation gets its own short event loop.
        """
        try:
            return asyncio.run(asyncio.wait_for(self._with_client(operation), TIMEOUT_SECONDS))
        except Exception as exc:  # timeout, protocol errors (often wrapped in an ExceptionGroup)
            # Why is for the log; a person is told only that the tools can't be reached (D180).
            logger.warning("expense tools unreachable (%s): %r", IN_PROCESS_SERVER, exc)
            raise ToolsUnavailableError(translatable(ChatText.TOOLS_UNREACHABLE)) from exc

    def _list(self) -> list[Tool]:
        """The server's tools, asked for once and then cached (shared by every bound copy)."""
        if self._listed.tools is None:

            async def list_tools(client: Client) -> list[Tool]:
                """Every tool the server offers."""
                return list((await client.list_tools()).tools)

            self._listed.tools = self._run(list_tools)
        return self._listed.tools

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
            # The list couldn't be fetched. This is asked after the tool has run, so raising would fail a turn whose
            # change is already saved: assume it may have changed data, as the spec says for any tool it can't vouch
            # for.
            return True
        tool = next((tool for tool in listed if tool.name == name), None)
        annotations = tool.annotations if tool else None
        return not (annotations and annotations.read_only_hint)

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutput:
        """Run one tool on the server, for the bound person, in its own session. A tool's own error comes back as
        ok=False. Raises RuntimeError if these tools aren't bound to anyone (a programming error)."""
        if self._owner_id is None:
            raise RuntimeError(UNBOUND)

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
        """The category names, read from the server's categories resource (fresh each turn; shared by everyone)."""

        async def read(client: Client) -> list[str]:
            """Read the resource and keep each category's name."""
            result = await client.read_resource(ResourceUri.CATEGORIES)
            categories = _CATEGORIES.validate_json(getattr(result.contents[0], "text", EMPTY_LIST_JSON))
            return [category.name for category in categories]

        return self._run(read)
