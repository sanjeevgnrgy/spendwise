"""The SpendWise MCP server: tools (actions) and resources (read-only data) for any MCP client.

Part of the mcp adapter. Every tool is a thin adapter: it turns an MCP call into commands and queries for the expenses
and categories modules, sent through the bus (or into a call to the reports module's use case), so MCP callers get
exactly the same rules as the REST API. An MCP client reads each tool's description and parameter descriptions to decide
when and how to call it.

This file only assembles the server: the tools live in tools/ (one file each), the resources in
resources.py. The composition root (bootstrap.py) calls create_server once, through module.py.
"""

from collections.abc import Callable

# The official MCP SDK. In SDK 2.x the class formerly called FastMCP is named MCPServer.
from mcp.server.mcpserver import MCPServer

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.modules import expenses, reports
from app.modules.mcp.contracts import SERVER_NAME
from app.modules.mcp.resources import register_resources
from app.modules.mcp.tools.add_expense import register_add_expense
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.delete_expense import register_delete_expense
from app.modules.mcp.tools.get_budgets import register_get_budgets
from app.modules.mcp.tools.get_expense import register_get_expense
from app.modules.mcp.tools.get_monthly_report import register_get_monthly_report
from app.modules.mcp.tools.get_summary import register_get_summary
from app.modules.mcp.tools.list_expenses import register_list_expenses
from app.modules.mcp.tools.set_budget import register_set_budget
from app.modules.mcp.tools.update_expense import register_update_expense
from app.modules.mcp.views import ExpenseViews

# What the server tells a client about itself when it connects.
INSTRUCTIONS = "Tools and resources for one person's expense tracker. Amounts are in rupees (INR) by default."

# Adds one tool to the server. Every registrar takes the same arguments (the server and a ToolContext), so adding a
# tool means writing a registrar and listing it below, without touching create_server.
ToolRegistrar = Callable[[MCPServer, ToolContext], None]

# The order the tools are registered in is the order clients list them, and so the order the model sees
# them: keep it.
TOOL_REGISTRARS: tuple[ToolRegistrar, ...] = (
    register_add_expense,
    register_list_expenses,
    register_get_expense,
    register_get_summary,
    register_update_expense,
    register_delete_expense,
    register_get_monthly_report,
    register_get_budgets,
    register_set_budget,
)


def create_server(
    bus: MessageBus, recorder: expenses.ExpenseRecorder, monthly_reports: reports.MonthlyReports, clock: Clock
) -> MCPServer:
    """Build the MCP server around a bus, the expenses recorder (its add and update tools save through it), the
    monthly reports (its get_monthly_report tool) and the clock (the budget tools' current month).
    Called once by the composition root (bootstrap.py).

    Registers every tool in TOOL_REGISTRARS order, then the resources. Raises RuntimeError if a tool lacks
    an argument the contract names (each registrar checks its own).
    """
    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    views = ExpenseViews(bus)
    context = ToolContext(
        bus=bus, views=views, recorder=recorder, monthly_reports=monthly_reports, clock=clock
    )
    for register in TOOL_REGISTRARS:
        register(server, context)
    register_resources(server, bus, views)
    return server
