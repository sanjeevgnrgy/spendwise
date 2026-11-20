"""The get_summary MCP tool: one month's totals, plus the previous month's total for comparison.

Part of the mcp adapter. register_get_summary adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order. The tool only translates: it asks the expenses module for two GetMonthlySummary, through
the bus, and answers with a typed result (MonthSpending). It only reads.

What clients see comes from the tool function: the SDK builds the input schema (titled
"get_summaryArguments") from its name, parameters and annotations, and the description from `description=`.
So those stay exactly as they are, and notes about the tool are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.months import YearMonth
from app.modules import expenses
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import MonthSpending, ToolName
from app.modules.mcp.tools.support import READS_ONLY, tool_errors
from app.modules.mcp.tools.context import ToolContext


def register_get_summary(server: MCPServer, context: ToolContext) -> None:
    """Add the get_summary tool: one month's totals (GetMonthlySummary) plus the previous month's total.
    """
    bus = context.bus

    # Two summaries, the month asked about and the one before; the database adds them up (GROUP BY), and
    # a month with no spending is a total of 0, not an error.
    @server.tool(
        name=ToolName.GET_SUMMARY,
        annotations=READS_ONLY,
        description="Get one month's total spending in INR (expenses in other currencies count at their INR amount) "
        "and the total for each category, biggest first, plus the previous month's total for comparison. "
        'Use it for questions like "where did my money go?".',
    )
    def get_summary(
        month: Annotated[str, Field(description="The month as YYYY-MM, e.g. '2026-11'.", pattern=YearMonth.PATTERN)],
    ) -> MonthSpending:
        with tool_errors():
            # The caller's spending only (caller.py, D191).
            owner = current_caller()
            this_month = YearMonth.parse(month)
            summary = bus.ask(expenses.GetMonthlySummary(owner_id=owner, month=this_month))
            earlier = this_month.shift(-1)
            previous = bus.ask(expenses.GetMonthlySummary(owner_id=owner, month=earlier))
            return MonthSpending(
                **summary.model_dump(exclude={"total"}),
                previous_month=expenses.MonthTotal(
                    month=previous.month, expense_count=previous.expense_count, total_minor=previous.total_minor
                ),
            )
