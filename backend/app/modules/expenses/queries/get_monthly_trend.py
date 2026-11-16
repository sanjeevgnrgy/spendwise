"""GetMonthlyTrend: the total for each of the last N months. The query, its handler and its answer.

A slice of the expenses module's read side; it never changes anything. module.py registers the handler with the
bus. The database groups by year and month, so only the totals travel to Python. MonthTotal and MonthlyTrend are
REST responses (MCP's get_summary uses MonthTotal too), so notes about them are `#` comments, not docstrings.
"""

from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy import extract, func
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.core.money import DEFAULT_CURRENCY, CurrencyCode
from app.core.months import YearMonth
from app.modules.expenses.models import Totalled
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.queries.month_range import in_month_range
from app.modules.expenses.values import MAX_TREND_MONTHS


# One month of a trend: its total and how many expenses it had. MCP's get_summary also uses it for the
# previous month.
class MonthTotal(Totalled):
    month: str = Field(pattern=YearMonth.PATTERN)
    expense_count: int


# GetMonthlyTrend's answer (GET /summary/trend), for the Dashboard's chart.
class MonthlyTrend(BaseModel):
    currency: str
    # Oldest month first, one entry per month, including months with no spending (total 0),
    # so a chart can draw them without gaps.
    months: list[MonthTotal]


# Asked by GET /summary/trend, with `until` set to the clock's today.
class GetMonthlyTrend(Query[MonthlyTrend]):
    """The owner's totals for the last `months` months, ending with the month that contains `until`."""

    owner_id: UserId
    months: int = Field(ge=1, le=MAX_TREND_MONTHS)
    until: date
    currency: CurrencyCode = DEFAULT_CURRENCY


def get_monthly_trend(ctx: Context, query: GetMonthlyTrend) -> MonthlyTrend:
    """The total for each of the last `months` months, ending with the month of `until`, oldest first.

    The database groups by year and month; every month in the range is then listed, with 0 for a month
    that had no expenses, so a chart has no gaps.
    """
    last = YearMonth.of(query.until)
    first = last.shift(-(query.months - 1))
    # SQLAlchemy's extract() is written once and rendered for each database: CAST(STRFTIME(...)) on
    # SQLite, which has no EXTRACT, and the standard EXTRACT(year/month ...) on Postgres. So this works on
    # SQLite today and Postgres later.
    year_of = extract("year", col(Expense.spent_on))
    month_of = extract("month", col(Expense.spent_on))
    statement = (
        select(year_of, month_of, func.count(col(Expense.id)), func.sum(Expense.amount_minor))
        .where(*in_month_range(query.owner_id, first.first_day(), last.shift(1).first_day(), query.currency))
        .group_by(year_of, month_of)
    )
    # int(): a database may hand back the year and month as decimals (Postgres's EXTRACT does).
    found = {YearMonth(int(y), int(m)): (count, total) for y, m, count, total in ctx.session.exec(statement)}
    # One entry per month, oldest first. A month with no spending is a real 0, not a missing point.
    trend = []
    for offset in range(query.months):
        month = first.shift(offset)
        count, total = found.get(month, (0, 0))
        trend.append(MonthTotal(month=str(month), expense_count=count, total_minor=total))
    return MonthlyTrend(currency=query.currency, months=trend)
