"""The get_budgets MCP tool: a month's spending against the caller's monthly budgets.

Part of the mcp adapter (Phase 27, D211). register_get_budgets adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it asks the budgets module's GetBudgetStatus through the bus and
answers with it. It only reads. In the assistant, a successful call is drawn as the budget card.

What clients see comes from the tool function (its name, parameters, annotations and `description=`), so notes about
the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.months import YearMonth
from app.modules import budgets
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ToolName
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.support import READS_ONLY, given, tool_errors

# The month's pattern, or nothing: "" means the current month.
MONTH_OR_EMPTY = f"({YearMonth.PATTERN})|^$"


def register_get_budgets(server: MCPServer, context: ToolContext) -> None:
    """Add the get_budgets tool: the caller's budgets for a month (the current one by default)."""
    bus, clock = context.bus, context.clock

    @server.tool(
        name=ToolName.GET_BUDGETS,
        annotations=READS_ONLY,
        description="Get the user's monthly budgets and how a month's spending (in INR) compares: the overall budget "
        "and one line per category, each with spent and, when it has a limit, limit, remaining (negative when "
        "over), used_percent and state (on_track; near_limit from 80%; over_limit). Also how much of the month "
        "has gone by. Use it for questions like 'how are my budgets?' or 'can I still spend on food?'.",
    )
    def get_budgets(
        month: Annotated[
            str, Field(description="The month as YYYY-MM; leave empty for the current month.", pattern=MONTH_OR_EMPTY)
        ] = "",
    ) -> budgets.BudgetStatus:
        with tool_errors():
            which = YearMonth.parse(month) if given(month) else YearMonth.of(clock.today())
            # The caller's own budgets only (caller.py, D191).
            return bus.ask(budgets.GetBudgetStatus(owner_id=current_caller(), month=which))
