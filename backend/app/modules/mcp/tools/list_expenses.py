"""The list_expenses MCP tool: the newest matching expenses, and how many match in all.

Part of the mcp adapter. register_list_expenses adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it turns its filters into the expenses module's ListExpenses,
sent through the bus, and answers with a typed result (ExpenseSearch) that names each category. It only reads.

What clients see comes from the tool function: the SDK builds the input schema (titled
"list_expensesArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.cqrs import MessageBus
from app.modules import expenses
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ExpenseSearch, ToolName
from app.modules.mcp.tools.support import READS_ONLY, given, tool_errors
from app.modules.mcp.views import ExpenseViews, to_view

# Each listed row is sent to the client's model and costs tokens, so lists are capped.
MAX_ROWS = 50


def register_list_expenses(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the list_expenses tool: the newest MAX_ROWS matching expenses, and how many match in all.

    The page's categories are named with one ListCategories, not one query per row.
    """

    # Filters combine with AND; "" leaves a filter out. A category is given by name and turned into an id
    # first, so an unknown name is a tool error that lists the real ones.
    @server.tool(
        name=ToolName.LIST_EXPENSES,
        annotations=READS_ONLY,
        description="List expenses, newest first, optionally filtered. Use it to find expense ids before "
        "updating or deleting, and to answer questions about specific expenses.",
    )
    def list_expenses(
        start_date: Annotated[str, Field(description="Only expenses on or after this date (YYYY-MM-DD).")] = "",
        end_date: Annotated[str, Field(description="Only expenses on or before this date (YYYY-MM-DD).")] = "",
        category: Annotated[str, Field(description="Only this category (by name).")] = "",
        merchant: Annotated[str, Field(description="Only this exact merchant (any letter case).")] = "",
        search: Annotated[str, Field(description="Only expenses whose merchant or note contains this text.")] = "",
    ) -> ExpenseSearch:
        with tool_errors():
            category_name = given(category)
            filters = expenses.ExpenseFilters(
                start_date=given(start_date),
                end_date=given(end_date),
                category_id=views.category_id(category_name) if category_name else None,
                merchant=given(merchant),
                search=given(search),
                # The database stops after MAX_ROWS and counts the rest, instead of sending every row.
                limit=MAX_ROWS,
            )
            # Only the caller's expenses are ever listed (caller.py, D191).
            found = bus.ask(expenses.ListExpenses(owner_id=current_caller(), filters=filters))
            names = views.category_names()
            return ExpenseSearch(
                count=found.total,
                expenses=[to_view(e, names) for e in found.items],
                truncated=found.total > len(found.items),
            )
