"""The get_monthly_report MCP tool: a month's report, worked out by the monthly-report skill's script (D209).

Part of the mcp adapter. register_get_monthly_report adds the tool to a server; server.py calls it, in
TOOL_REGISTRARS order (last, so the tools before it reach the model as they did). The tool only translates: it asks
the reports module's use case for the caller's figures and answers with them (reports.MonthlyReport). It only reads.
In the assistant, a successful call is drawn as the report card, with its Download CSV and Download report (.md)
buttons (assistant/a2ui/report_card.py).

What clients see comes from the tool function: the SDK builds the input schema from its name, parameters and
annotations, and the description from `description=`. So those stay exactly as they are, and notes about the tool
are `#` comments, not docstrings.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from app.core.months import YearMonth
from app.modules import reports
from app.modules.mcp.caller import current_caller
from app.modules.mcp.contracts import ToolName
from app.modules.mcp.tools.context import ToolContext
from app.modules.mcp.tools.support import READS_ONLY, tool_errors


def register_get_monthly_report(server: MCPServer, context: ToolContext) -> None:
    """Add the get_monthly_report tool: the caller's report for one month, from the reports module."""
    monthly_reports = context.monthly_reports

    @server.tool(
        name=ToolName.GET_MONTHLY_REPORT,
        annotations=READS_ONLY,
        description="Get one month's spending report, in INR: the total against the previous month (change_percent "
        "is null when the previous month had nothing), the totals and shares by category and by payment method, "
        "the five biggest expenses and the daily average. The figures are worked out by SpendWise, never by you. "
        "The user sees them as a report card with buttons to download the report as CSV or markdown.",
    )
    def get_monthly_report(
        month: Annotated[str, Field(description="The month as YYYY-MM, e.g. '2026-11'.", pattern=YearMonth.PATTERN)],
    ) -> reports.MonthlyReport:
        with tool_errors():
            # The caller's own expenses only (caller.py, D191).
            return monthly_reports.figures(current_caller(), YearMonth.parse(month))
