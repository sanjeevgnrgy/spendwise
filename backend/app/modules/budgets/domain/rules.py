"""How a month's spending is measured against a budget, and how much of a month has gone by.

The budgets module's domain rules: pure functions (no database, no clock of their own), used by the status query
(queries/get_budget_status.py).
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.months import YearMonth
from app.modules.budgets.values import FULL_PERCENT, NEAR_LIMIT_PERCENT, BudgetState

ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class Standing:
    """Spending against a limit: what's left (negative once over), the share used in percent, and the state."""

    remaining_minor: int
    used_percent: Decimal
    state: BudgetState


def percent(part: int, whole: int) -> Decimal:
    """`part` as a percentage of `whole` (above zero), to one decimal, rounded half up."""
    return (Decimal(part) * FULL_PERCENT / Decimal(whole)).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def standing(spent_minor: int, limit_minor: int) -> Standing:
    """Where `spent_minor` stands against `limit_minor` (both in paise; the limit is above zero).

    The state is decided on exact paise, not the rounded percent: ₹8,000.01 against ₹8,000 is over the limit even
    though it rounds to 100.0%.
    """
    if spent_minor > limit_minor:
        state = BudgetState.OVER_LIMIT
    elif spent_minor * FULL_PERCENT >= limit_minor * NEAR_LIMIT_PERCENT:
        state = BudgetState.NEAR_LIMIT
    else:
        state = BudgetState.ON_TRACK
    return Standing(limit_minor - spent_minor, percent(spent_minor, limit_minor), state)


def month_elapsed_percent(month: YearMonth, today: date) -> Decimal:
    """How much of `month` has gone by on `today`, in percent: all of a past month, none of a future one, and for the
    running month the days so far, today included (on the 15th of a 30-day month, 50.0)."""
    if YearMonth.of(today) > month:
        return Decimal(FULL_PERCENT)
    if YearMonth.of(today) < month:
        return Decimal(0)
    return percent(today.day, calendar.monthrange(month.year, month.month)[1])
