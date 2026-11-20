"""The set_budget MCP tool: set (or change) one of the caller's monthly budgets, overall or for a category.

Part of the mcp adapter (Phase 27, D211). register_set_budget adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: the category arrives as a name and becomes an id (an unknown name is
a tool error listing the real ones), the budgets module's SetBudget sets the limit, and the answer is the current
month's status, which the assistant draws as the budget card. Removing a limit isn't a tool: people do it on the
Budgets page.

What clients see comes from the tool function (its name, parameters, annotations and `description=`), so notes about
the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.months import YearMonth
from app.modules import budgets
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ResourceUri, ToolName
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.support import ADDS_DATA, given, tool_errors


def register_set_budget(server: MCPServer, context: ToolContext) -> None:
    """Add the set_budget tool: one monthly limit, then the current month's status."""
    bus, views, clock = context.bus, context.views, context.clock

    # Setting a limit replaces the scope's old one; it's a standing amount (every month until changed), so nothing
    # is lost that can't be set again: no confirmation interlock.
    @server.tool(
        name=ToolName.SET_BUDGET,
        annotations=ADDS_DATA,
        description="Set the user's monthly budget (a spending limit in INR that applies every month until changed): "
        "for one category, or with no category for all spending together. Replaces that budget's old limit. "
        "Answers with this month's budgets, which the user sees as a card.",
    )
    def set_budget(
        limit: Annotated[str | float, Field(description="The monthly limit in rupees, e.g. '8000'.")],
        category: Annotated[
            str, Field(description=f"Category name (see {ResourceUri.CATEGORIES}); leave empty for the overall budget.")
        ] = "",
    ) -> budgets.BudgetStatus:
        with tool_errors():
            # The caller's own budget (caller.py, D191); never a person named in the arguments.
            owner = current_caller()
            category_id = views.category_id(category) if given(category) else None
            bus.execute(budgets.SetBudget(owner_id=owner, category_id=category_id, limit=str(limit)))
            return bus.ask(budgets.GetBudgetStatus(owner_id=owner, month=YearMonth.of(clock.today())))
