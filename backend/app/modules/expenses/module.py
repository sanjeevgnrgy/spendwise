"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it."""

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
    bus.register(CreateExpense, commands.create_expense)
    bus.register(UpdateExpense, commands.update_expense)
    bus.register(DeleteExpense, commands.delete_expense)
    bus.register(GetExpense, queries.get_expense)
    bus.register(ListExpenses, queries.list_expenses)
    bus.register(GetMonthlySummary, queries.monthly_summary)
    bus.register(GetMonthlyTrend, queries.monthly_trend)


__all__ = ["TABLES", "register_handlers", "router"]
