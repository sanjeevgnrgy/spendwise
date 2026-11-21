"""BudgetWatch: which of a person's budgets a save of an expense pushed near or over their limit (D211, D212).

The budgets module's use case (application/). It asks for the status of the expense's month before the save and after
it, through the bus (each ask its own short unit of work, so the save in between never runs inside one), and compares
them with domain/alerts.crossed. It implements the expenses module's SaveWatcher port (watch: alerts as texts, for the
REST routes' notices), and gives the MCP tools add_expense and update_expense the alerts themselves (around).
"""

from collections.abc import Callable
from datetime import date
from typing import TypeVar

from app.core.cqrs import MessageBus
from app.core.i18n import Language
from app.core.ids import UserId
from app.core.months import YearMonth
from app.modules.budgets.domain.alerts import crossed
from app.modules.budgets.i18n import alert_text
from app.modules.budgets.models import BudgetAlert
from app.modules.budgets.queries.get_budget_status import GetBudgetStatus

T = TypeVar("T")


class BudgetWatch:
    """Looks at a person's budgets around a save of one of their expenses."""

    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus

    def around(self, owner_id: UserId, day: date, save: Callable[[], T]) -> tuple[T, list[BudgetAlert]]:
        """Run `save` (it records or changes an expense dated `day`) and return its result with the alerts: the
        owner's budgets for that month that the save moved near or over their limit."""
        month = YearMonth.of(day)
        before = self._bus.ask(GetBudgetStatus(owner_id=owner_id, month=month))
        result = save()
        after = self._bus.ask(GetBudgetStatus(owner_id=owner_id, month=month))
        return result, crossed(before, after)

    def watch(self, owner_id: UserId, day: date, save: Callable[[], T], language: Language) -> tuple[T, list[str]]:
        """The expenses module's SaveWatcher: like around(), with each alert written as a sentence in `language`."""
        result, alerts = self.around(owner_id, day, save)
        return result, [alert_text(alert, language) for alert in alerts]
