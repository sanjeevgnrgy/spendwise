"""What every MCP tool registrar is given: ToolContext (the bus, the expense views, the expenses recorder, the
monthly reports and the clock).

Part of the mcp adapter. server.create_server builds one and hands it to each registrar in TOOL_REGISTRARS, so adding
a dependency means adding a field here, not changing every registrar's signature.
"""

from dataclasses import dataclass

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.modules import expenses, reports
from app.modules.mcp.views import ExpenseViews


@dataclass(frozen=True)
class ToolContext:
    """The bus (commands and queries), the views (an expense as tools show it, category names to ids), the
    recorder, which saves expenses (converting an amount in another currency to INR first, D204), the monthly
    reports, which the monthly-report skill's script works out (D209), and the clock (today's month, for the
    budget tools)."""

    bus: MessageBus
    views: ExpenseViews
    recorder: expenses.ExpenseRecorder
    monthly_reports: reports.MonthlyReports
    clock: Clock
