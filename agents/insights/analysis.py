"""The insights agent's numbers: totals, trends, unusual spends and the month-end forecast, worked out by code.

Domain logic of the insights agent: pure functions over the expenses sent, no model and no I/O (the executor calls
analyse, then has the model write the tips from its result). Money is added up in paise and written back as decimal
strings; nothing goes through a float. The rules (D205):

- trends: each category's total this month against the month before, biggest first;
- unusual: an expense at least UNUSUAL_FACTOR times its category's median in the data (a category needs MIN_SAMPLES
  expenses for a median to mean anything) and at least MIN_UNUSUAL_PAISE;
- forecast: for the month that's still running, the spending so far divided by the days gone, times the month's days.
"""

import calendar
import statistics
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.money import BASE_CURRENCY, paise_to_rupees, rupees_to_paise
from app.core.months import YearMonth
from insights.contract import CategoryTrend, ExpenseRow, Forecast, Insights, UnusualSpend

MAX_TRENDS = 8
MAX_UNUSUAL = 5
UNUSUAL_FACTOR = 3
MIN_SAMPLES = 4
MIN_UNUSUAL_PAISE = 50_000  # ₹500: a ₹60 chai at three times the usual ₹20 isn't worth pointing out
FORECAST_METHOD = "linear"
ONE_DECIMAL = Decimal("0.1")
PERCENT = 100


def analyse(expenses: list[ExpenseRow], month: YearMonth, today: date) -> Insights:
    """Everything about `month` but the tips (left empty): totals, trends, unusual spends, and the forecast if `month`
    is today's."""
    this = [row for row in expenses if YearMonth.of(row.spent_on) == month]
    before = [row for row in expenses if YearMonth.of(row.spent_on) == month.shift(-1)]
    total = sum(_paise(row) for row in this)
    return Insights(
        month=str(month),
        currency=BASE_CURRENCY,
        total=_money(total),
        previous_total=_money(sum(_paise(row) for row in before)),
        expense_count=len(this),
        trends=_trends(this, before),
        unusual=_unusual(this, expenses),
        forecast=_forecast(total, month, today),
        tips=[],
    )


def _paise(row: ExpenseRow) -> int:
    """The row's amount in paise."""
    return rupees_to_paise(row.amount)


def _money(paise: int) -> str:
    """Paise as a decimal string ("1250.50")."""
    return str(paise_to_rupees(paise))


def _by_category(rows: list[ExpenseRow]) -> dict[str, int]:
    """Each category's total in paise."""
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[row.category] += _paise(row)
    return totals


def _trends(this: list[ExpenseRow], before: list[ExpenseRow]) -> list[CategoryTrend]:
    """This month's categories, biggest first, each against the month before."""
    now, then = _by_category(this), _by_category(before)
    trends = []
    for category, paise in sorted(now.items(), key=lambda item: item[1], reverse=True)[:MAX_TRENDS]:
        previous = then.get(category, 0)
        change = None
        if previous:
            change = str((Decimal(paise - previous) * PERCENT / previous).quantize(ONE_DECIMAL, ROUND_HALF_UP))
        trends.append(CategoryTrend(category=category, this_month=_money(paise), previous_month=_money(previous),
                                    change_percent=change))
    return trends


def _unusual(this: list[ExpenseRow], everything: list[ExpenseRow]) -> list[UnusualSpend]:
    """This month's expenses far above their category's median in all the data sent, biggest first."""
    samples: dict[str, list[int]] = defaultdict(list)
    for row in everything:
        samples[row.category].append(_paise(row))
    medians = {
        category: statistics.median(values) for category, values in samples.items() if len(values) >= MIN_SAMPLES
    }
    unusual = []
    for row in this:
        usual = medians.get(row.category)
        paise = _paise(row)
        if usual and paise >= MIN_UNUSUAL_PAISE and paise >= UNUSUAL_FACTOR * usual:
            unusual.append((paise, row, int(usual)))
    unusual.sort(key=lambda item: item[0], reverse=True)
    return [
        UnusualSpend(spent_on=row.spent_on, merchant=row.merchant, category=row.category, amount=_money(paise),
                     usual=_money(usual), times=str((Decimal(paise) / usual).quantize(ONE_DECIMAL, ROUND_HALF_UP)))
        for paise, row, usual in unusual[:MAX_UNUSUAL]
    ]


def _forecast(total: int, month: YearMonth, today: date) -> Forecast | None:
    """Where today's month is heading, linearly; None for any other month (a past one is complete)."""
    if month != YearMonth.of(today):
        return None
    days = calendar.monthrange(month.year, month.month)[1]
    projected = (Decimal(total) * days / today.day).quantize(Decimal(1), ROUND_HALF_UP)
    return Forecast(spent_so_far=_money(total), days_elapsed=today.day, days_in_month=days,
                    month_end_total=_money(int(projected)), method=FORECAST_METHOD)
