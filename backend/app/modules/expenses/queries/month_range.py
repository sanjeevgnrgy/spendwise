"""The WHERE conditions for "one person's expenses in these months, in this currency", shared by the summary and
trend query slices.

Part of the expenses module's read side, used by get_monthly_summary.py and get_monthly_trend.py; it changes
nothing.
"""

from datetime import date
from typing import Any

from app.modules.expenses.persistence.tables import Expense


def in_month_range(owner_id: int, start: date, end: date, currency: str) -> tuple[Any, ...]:
    """`owner_id`'s expenses from `start` up to, not including, `end`: "before the next month" avoids month lengths.

    Only that person's rows are ever added up (D190). Also limits to one currency: totals in rupees and dollars can't
    be added together.
    """
    return (
        Expense.owner_id == owner_id,
        Expense.spent_on >= start,
        Expense.spent_on < end,
        Expense.currency == currency,
    )
