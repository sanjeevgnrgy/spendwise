"""Watching a save for budget alerts: the month's budgets before and after, compared by the budgets module.

Part of the mcp adapter, used by add_expense and update_expense (Phase 27, D211). The rule (which changes are alerts)
is the budgets module's (budgets.crossed); this only asks for the status of the expense's month before the save and
after it, through the bus. Each ask is its own short unit of work, so the save in between (which may wait for an
exchange rate) never runs inside one.
"""

from collections.abc import Callable
from datetime import date
from typing import TypeVar

from app.core.cqrs import MessageBus
from app.core.ids import UserId
from app.core.months import YearMonth
from app.modules import budgets

T = TypeVar("T")

# What add_expense's and update_expense's descriptions tell the model about the alerts in their results.
BUDGET_ALERTS_NOTE = (
    "The result's budget_alerts lists budgets this save pushed near (80%) or over their monthly limit; "
    "if there are any, mention them in one short sentence."
)


def watch_budgets(
    bus: MessageBus, owner: UserId, day: date, save: Callable[[], T]
) -> tuple[T, list[budgets.BudgetAlert]]:
    """Run `save` (which records or changes an expense dated `day`) and return its result with the alerts: the
    owner's budgets for that month that the save moved near or over their limit."""
    month = YearMonth.of(day)
    before = bus.ask(budgets.GetBudgetStatus(owner_id=owner, month=month))
    result = save()
    after = bus.ask(budgets.GetBudgetStatus(owner_id=owner, month=month))
    return result, budgets.crossed(before, after)
