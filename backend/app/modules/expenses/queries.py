"""Query handlers: read expenses straight into the data callers get. They never change anything.

The database does the filtering, counting and adding up (WHERE, COUNT, GROUP BY), so only results
travel to Python, never every row.
"""

from datetime import date
from typing import Any

from sqlalchemy import extract, func, or_
from sqlmodel import col, select

from app.core.cqrs import Context
from app.core.errors import NotFoundError
from app.core.months import YearMonth
from app.modules import categories
from app.modules.expenses.contracts import (
    CategoryTotal,
    ExpenseList,
    ExpenseRead,
    GetExpense,
    GetMonthlySummary,
    GetMonthlyTrend,
    ListExpenses,
    MonthlySummary,
    MonthlyTrend,
    MonthTotal,
)
from app.modules.expenses.tables import Expense


def get_expense(ctx: Context, query: GetExpense) -> ExpenseRead:
    row = ctx.session.get(Expense, query.expense_id)
    if row is None:
        raise NotFoundError(f"Expense {query.expense_id} not found")
    return ExpenseRead.model_validate(row)


def _matching(query: ListExpenses) -> list[Any]:
    # Each condition is added only when that filter was given, so no filters means "everything".
    conditions: list[Any] = []
    if query.start_date:
        conditions.append(Expense.spent_on >= query.start_date)
    if query.end_date:
        conditions.append(Expense.spent_on <= query.end_date)
    if query.category_id is not None:
        conditions.append(Expense.category_id == query.category_id)
    if query.merchant:
        # The database lowercases both sides. Python's .lower() handles letters like "É" that SQLite's
        # lower() leaves alone, so mixing the two would make "CAFÉ" never match itself.
        conditions.append(func.lower(Expense.merchant) == func.lower(query.merchant))
    if query.search:
        # autoescape: a % or _ the user types is searched for literally, not used as a wildcard.
        conditions.append(
            or_(
                col(Expense.merchant).icontains(query.search, autoescape=True),
                col(Expense.note).icontains(query.search, autoescape=True),
            )
        )
    return conditions


def list_expenses(ctx: Context, query: ListExpenses) -> ExpenseList:
    conditions = _matching(query)
    total = ctx.session.exec(select(func.count()).select_from(Expense).where(*conditions)).one()
    rows = ctx.session.exec(
        select(Expense)
        .where(*conditions)
        # Newest first: that's how people read a list of expenses.
        .order_by(col(Expense.spent_on).desc(), col(Expense.id).desc())
        .offset(query.offset)
        .limit(query.limit)
    )
    return ExpenseList(items=[ExpenseRead.model_validate(row) for row in rows], total=total)


def _in_range(start: date, end: date, currency: str) -> tuple[Any, ...]:
    """From `start` up to, not including, `end`: querying "before the next month" avoids month lengths."""
    return Expense.spent_on >= start, Expense.spent_on < end, Expense.currency == currency


def monthly_summary(ctx: Context, query: GetMonthlySummary) -> MonthlySummary:
    statement = (
        select(Expense.category_id, func.count(col(Expense.id)), func.sum(Expense.amount_minor))
        .where(*_in_range(query.month.first_day(), query.month.shift(1).first_day(), query.currency))
        .group_by(col(Expense.category_id))
    )
    names = {c.id: c.name for c in ctx.bus.ask(categories.ListCategories())}
    by_category = sorted(
        (
            CategoryTotal(
                category_id=category_id,
                category_name=names.get(category_id, categories.UNKNOWN_CATEGORY),
                expense_count=count,
                total_minor=total,
            )
            for category_id, count, total in ctx.session.exec(statement)
        ),
        key=lambda t: t.total_minor,
        reverse=True,
    )
    return MonthlySummary(
        month=str(query.month),
        currency=query.currency,
        expense_count=sum(t.expense_count for t in by_category),
        total_minor=sum(t.total_minor for t in by_category),
        by_category=by_category,
    )


def monthly_trend(ctx: Context, query: GetMonthlyTrend) -> MonthlyTrend:
    last = YearMonth.of(query.until)
    first = last.shift(-(query.months - 1))
    # EXTRACT(year/month ...) is standard SQL, so this works on SQLite today and Postgres later.
    year_of = extract("year", col(Expense.spent_on))
    month_of = extract("month", col(Expense.spent_on))
    statement = (
        select(year_of, month_of, func.count(col(Expense.id)), func.sum(Expense.amount_minor))
        .where(*_in_range(first.first_day(), last.shift(1).first_day(), query.currency))
        .group_by(year_of, month_of)
    )
    found = {YearMonth(int(y), int(m)): (count, total) for y, m, count, total in ctx.session.exec(statement)}
    # One entry per month, oldest first. A month with no spending is a real 0, not a missing point.
    trend = []
    for offset in range(query.months):
        month = first.shift(offset)
        count, total = found.get(month, (0, 0))
        trend.append(MonthTotal(month=str(month), expense_count=count, total_minor=total))
    return MonthlyTrend(currency=query.currency, months=trend)
