"""The MCP tools that only read: list_expenses, get_expense and get_summary.

Part of the mcp adapter. Each register_* function adds one tool to a server; server.py calls them in the
order clients list the tools. A tool only translates: it turns its arguments into a query for the expenses
module, sends it through the bus, and answers with typed results (contracts.py) that name each category.

What clients see comes from each tool function: the SDK builds the input schema (titled
"<function name>Arguments") from its name, parameters and annotations, and the description from
`description=`. So those stay exactly as they are, and notes about a tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.cqrs import MessageBus
from app.core.money import CURRENCY_PATTERN, DEFAULT_CURRENCY
from app.core.months import YearMonth
from app.modules import expenses
from app.modules.mcp.contracts import EXPENSE_ID_ARGUMENT, ExpenseFound, ExpenseSearch, MonthSpending, ToolName
from app.modules.mcp.tool_support import READS_ONLY, ExpenseIdArg, given, require_arguments, tool_errors
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
            found = bus.ask(
                expenses.ListExpenses(
                    start_date=given(start_date),
                    end_date=given(end_date),
                    category_id=views.category_id(category_name) if category_name else None,
                    merchant=given(merchant),
                    search=given(search),
                    # The database stops after MAX_ROWS and counts the rest, instead of sending every row.
                    limit=MAX_ROWS,
                )
            )
            names = views.category_names()
            return ExpenseSearch(
                count=found.total,
                expenses=[to_view(e, names) for e in found.items],
                truncated=found.total > len(found.items),
            )


def register_get_expense(server: MCPServer, bus: MessageBus, views: ExpenseViews) -> None:
    """Add the get_expense tool: one expense by id, or a "not found" tool error.

    Raises RuntimeError at start-up if the tool lacks the argument the contract names (expense_id).
    """

    # The assistant calls it to show an expense (and its version) before a delete is approved.
    @server.tool(
        name=ToolName.GET_EXPENSE,
        annotations=READS_ONLY,
        description="Get one expense by its id, e.g. to show it to the user before changing or deleting it.",
    )
    def get_expense(expense_id: ExpenseIdArg) -> ExpenseFound:
        with tool_errors():
            return ExpenseFound(expense=views.find(expense_id))

    require_arguments(get_expense, EXPENSE_ID_ARGUMENT)


def register_get_summary(server: MCPServer, bus: MessageBus, _views: ExpenseViews) -> None:
    """Add the get_summary tool: one month's totals (GetMonthlySummary) plus the previous month's total.

    `_views` is unused: every registrar takes the same three arguments (server.ToolRegistrar).
    """

    # Two summaries, the month asked about and the one before; the database adds them up (GROUP BY), and
    # a month with no spending is a total of 0, not an error.
    @server.tool(
        name=ToolName.GET_SUMMARY,
        annotations=READS_ONLY,
        description="Get one month's total spending and the total for each category, biggest first, plus the "
        'previous month\'s total for comparison. Use it for questions like "where did my money go?".',
    )
    def get_summary(
        month: Annotated[str, Field(description="The month as YYYY-MM, e.g. '2026-11'.", pattern=YearMonth.PATTERN)],
        currency: Annotated[
            str, Field(description="ISO currency code. INR unless asked otherwise.", pattern=CURRENCY_PATTERN)
        ] = DEFAULT_CURRENCY,
    ) -> MonthSpending:
        with tool_errors():
            this_month = YearMonth.parse(month)
            summary = bus.ask(expenses.GetMonthlySummary(month=this_month, currency=currency))
            previous = bus.ask(expenses.GetMonthlySummary(month=this_month.shift(-1), currency=currency))
            return MonthSpending(
                **summary.model_dump(exclude={"total"}),
                previous_month=expenses.MonthTotal(
                    month=previous.month, expense_count=previous.expense_count, total_minor=previous.total_minor
                ),
            )
