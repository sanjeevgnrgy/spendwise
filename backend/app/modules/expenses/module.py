"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The expenses module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
Each message and its handler come from the same slice file, in commands/ or queries/.
"""

from app.core.cqrs import MessageBus
from app.modules.expenses.api import router
from app.modules.expenses.commands.create_expense import CreateExpense, create_expense
from app.modules.expenses.commands.delete_expense import DeleteExpense, delete_expense
from app.modules.expenses.commands.update_expense import UpdateExpense, update_expense
from app.modules.expenses.persistence.tables import TABLES
from app.modules.expenses.queries.get_expense import GetExpense, get_expense
from app.modules.expenses.queries.get_monthly_summary import GetMonthlySummary, get_monthly_summary
from app.modules.expenses.queries.get_monthly_trend import GetMonthlyTrend, get_monthly_trend
from app.modules.expenses.queries.list_expenses import ListExpenses, list_expenses


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(CreateExpense, create_expense)
    bus.register(UpdateExpense, update_expense)
    bus.register(DeleteExpense, delete_expense)
    bus.register(GetExpense, get_expense)
    bus.register(ListExpenses, list_expenses)
    bus.register(GetMonthlySummary, get_monthly_summary)
    bus.register(GetMonthlyTrend, get_monthly_trend)


__all__ = ["TABLES", "register_handlers", "router"]
