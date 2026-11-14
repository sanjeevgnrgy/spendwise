"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The expenses module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
"""

from app.core.cqrs import MessageBus
from app.modules.expenses import commands, queries
from app.modules.expenses.api import router
from app.modules.expenses.contracts import (
    CreateExpense,
    DeleteExpense,
    GetExpense,
    GetMonthlySummary,
    GetMonthlyTrend,
    ListExpenses,
    UpdateExpense,
)
from app.modules.expenses.tables import TABLES


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(CreateExpense, commands.create_expense)
    bus.register(UpdateExpense, commands.update_expense)
    bus.register(DeleteExpense, commands.delete_expense)
    bus.register(GetExpense, queries.get_expense)
    bus.register(ListExpenses, queries.list_expenses)
    bus.register(GetMonthlySummary, queries.monthly_summary)
    bus.register(GetMonthlyTrend, queries.monthly_trend)


__all__ = ["TABLES", "register_handlers", "router"]
