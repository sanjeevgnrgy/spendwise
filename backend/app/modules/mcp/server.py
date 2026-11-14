"""The SpendWise MCP server: tools (actions) and resources (read-only data) for any MCP client.

Part of the mcp adapter. Every tool is a thin adapter: it turns an MCP call into commands and queries for
the expenses and categories modules, sent through the bus, so MCP callers get exactly the same rules as the
REST API. An MCP client reads each tool's description and parameter descriptions to decide when and how to
call it.

This file only assembles the server: the tools live in read_tools.py and write_tools.py, the resources in
resources.py. The composition root (bootstrap.py) calls create_server once, through module.py.
"""

from collections.abc import Callable

# The official MCP SDK. In SDK 2.x the class formerly called FastMCP is named MCPServer.
from mcp.server.mcpserver import MCPServer

from app.core.cqrs import MessageBus
from app.modules.mcp.contracts import SERVER_NAME
from app.modules.mcp.read_tools import register_get_expense, register_get_summary, register_list_expenses
from app.modules.mcp.resources import register_resources
from app.modules.mcp.views import ExpenseViews
from app.modules.mcp.write_tools import register_add_expense, register_delete_expense, register_update_expense

# What the server tells a client about itself when it connects.
INSTRUCTIONS = "Tools and resources for one person's expense tracker. Amounts are in rupees (INR) by default."

# Adds one tool to the server. Every registrar takes the same arguments, so adding a tool means writing a
# registrar and listing it below, without touching create_server.
ToolRegistrar = Callable[[MCPServer, MessageBus, ExpenseViews], None]

# The order the tools are registered in is the order clients list them, and so the order the model sees
# them: keep it.
TOOL_REGISTRARS: tuple[ToolRegistrar, ...] = (
    register_add_expense,
    register_list_expenses,
    register_get_expense,
    register_get_summary,
    register_update_expense,
    register_delete_expense,
)


def create_server(bus: MessageBus) -> MCPServer:
    """Build the MCP server around a bus. Called once by the composition root (bootstrap.py).

    Registers every tool in TOOL_REGISTRARS order, then the resources. Raises RuntimeError if a tool lacks
    an argument the contract names (each registrar checks its own).
    """
    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    views = ExpenseViews(bus)
    for register in TOOL_REGISTRARS:
        register(server, bus, views)
    register_resources(server, bus, views)
    return server
