"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The budgets module's wiring. bootstrap.py calls register_handlers() when it builds the bus, builds the budget watch with
create_watch(), mounts `router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py
instead. Each message and its handler come from the same slice file, in commands/ or queries/.
"""

from app.core.cqrs import MessageBus
from app.modules.budgets.api import router
from app.modules.budgets.application.budget_watch import BudgetWatch
from app.modules.budgets.commands.remove_budget import RemoveBudget, remove_budget
from app.modules.budgets.commands.set_budget import SetBudget, set_budget
from app.modules.budgets.persistence.tables import TABLES
from app.modules.budgets.queries.get_budget_status import GetBudgetStatus, get_budget_status


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries. Registering a message twice
    raises ValueError (a wiring mistake)."""
    bus.register(SetBudget, set_budget)
    bus.register(RemoveBudget, remove_budget)
    bus.register(GetBudgetStatus, get_budget_status)


def create_watch(bus: MessageBus) -> BudgetWatch:
    """The budget watch, around the bus: the expenses routes' SaveWatcher and the MCP save tools' alerts (D212)."""
    return BudgetWatch(bus)


__all__ = ["TABLES", "create_watch", "register_handlers", "router"]
