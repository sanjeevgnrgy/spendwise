"""SaveWatcher: the port through which something outside the expenses module looks at a save and has notices for
the person (D212).

The expenses module's application layer. The REST routes (api.py) run every create and update through it and send its
notices with the saved expense. The budgets module implements it (budgets.BudgetWatch: budgets a save pushed near or
over their limit), and the composition root plugs it in, so the expenses module never imports budgets (budgets
already depends on expenses: dependency inversion keeps that one way).
"""

from collections.abc import Callable
from datetime import date
from typing import Protocol, TypeVar

from app.core.i18n import Language
from app.core.ids import UserId

T = TypeVar("T")


class SaveWatcher(Protocol):
    """Runs a save of one of a person's expenses and says what it notices about it."""

    def watch(self, owner_id: UserId, day: date, save: Callable[[], T], language: Language) -> tuple[T, list[str]]:
        """Run `save` (it records or changes `owner_id`'s expense dated `day`) and return its result with the
        notices for the person, written in `language` (texts for people, D179), or none."""
        ...
