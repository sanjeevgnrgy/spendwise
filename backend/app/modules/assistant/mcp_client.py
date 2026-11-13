"""The assistant's MCP client: finds and calls the expense tools over MCP (Streamable HTTP).

The assistant knows only a URL (settings.mcp_url). What tools exist, what arguments they
take and how they work is all learned from the MCP server at runtime.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.core.config import settings
from app.core.errors import ExternalServiceError

T = TypeVar("T")

# Give up if the MCP server doesn't answer in this many seconds, rather than hang the chat.
TIMEOUT_SECONDS = 15

# The only JSON-schema keywords passed on to Gemini; the rest (title, default, ...) are noise to it.
_KEPT_KEYWORDS = ("type", "description", "enum", "items", "format")


class McpUnavailableError(ExternalServiceError):
    """The MCP server couldn't be reached, or didn't answer in time."""


@dataclass
class ToolResult:
    text: str
    ok: bool


async def _with_session(operation: Callable[[ClientSession], Awaitable[T]]) -> T:
    async with streamable_http_client(settings.mcp_url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            return await operation(session)


def _run(operation: Callable[[ClientSession], Awaitable[T]]) -> T:
    """Connect, do one thing, disconnect.

    The MCP SDK is async, but the agent runs in a plain worker thread (see router.py), so each
    operation gets its own short event loop. A connection per operation is simple and fine
    here: the server is stateless and usually on the same machine.
    """
    try:
        return asyncio.run(asyncio.wait_for(_with_session(operation), TIMEOUT_SECONDS))
    except Exception as exc:  # connection refused, timeout, protocol errors (often wrapped in an ExceptionGroup)
        raise McpUnavailableError(f"Could not reach the MCP server at {settings.mcp_url}") from exc


def _simplify(prop: dict[str, Any]) -> dict[str, Any]:
    # Optional arguments arrive as anyOf [X, null]; Gemini just needs X (and "not required").
    if "anyOf" in prop:
        real = next((option for option in prop["anyOf"] if option.get("type") != "null"), {})
        prop = {**prop, **real}
    return {key: prop[key] for key in _KEPT_KEYWORDS if key in prop}


def _to_declaration(tool: Any) -> dict[str, Any]:
    """Turn one MCP tool description into a Gemini function declaration."""
    schema = tool.input_schema or {}
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or "",
        "parameters": {
            "type": "object",
            "properties": {name: _simplify(prop) for name, prop in schema.get("properties", {}).items()},
            "required": schema.get("required", []),
        },
    }


_declarations: list[dict[str, Any]] | None = None


def tool_declarations() -> list[dict[str, Any]]:
    """Gemini function declarations for every tool the MCP server offers.

    Fetched on first use and then remembered. It can't be done while the app starts: by
    default the MCP server is this same app, which isn't answering requests yet at that
    point. Restart the app to pick up tools added to the server later.
    """
    global _declarations
    if _declarations is None:

        async def list_tools(session: ClientSession) -> list[dict[str, Any]]:
            return [_to_declaration(tool) for tool in (await session.list_tools()).tools]

        _declarations = _run(list_tools)
    return _declarations


def call_tool(name: str, arguments: dict[str, Any]) -> ToolResult:
    async def call(session: ClientSession) -> ToolResult:
        result = await session.call_tool(name, arguments)
        text = "".join(getattr(part, "text", "") for part in result.content)
        # is_error means the tool ran and reported a problem (e.g. "Unknown category"); that's
        # useful to the model, so it's returned rather than raised.
        return ToolResult(text=text, ok=not result.is_error)

    return _run(call)


def category_names() -> list[str]:
    """The category names, read from the server's expenses://categories resource."""

    async def read(session: ClientSession) -> list[str]:
        result = await session.read_resource("expenses://categories")
        return [category["name"] for category in json.loads(result.contents[0].text)]

    return _run(read)
