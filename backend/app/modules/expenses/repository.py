"""The only code that reads or writes the expenses table. Queries only, no business rules."""

from datetime import date
from typing import Any

from sqlalchemy import extract, func, or_
from sqlmodel import Session, col, select

from app.modules.expenses.models import Expense
from app.modules.expenses.schemas import ExpenseFilters


def add(session: Session, expense: Expense) -> Expense:
    session.add(expense)
    session.commit()
    # Reload so values the database generated (the new id) are filled in.
    session.refresh(expense)
    return expense


def get(session: Session, expense_id: int) -> Expense | None:
    return session.get(Expense, expense_id)


def search(session: Session, filters: ExpenseFilters) -> list[Expense]:
    statement = select(Expense)
    # Each condition is added only when that filter was given, so no filters means "everything".
    if filters.start_date:
        statement = statement.where(Expense.spent_on >= filters.start_date)
    if filters.end_date:
        statement = statement.where(Expense.spent_on <= filters.end_date)
    if filters.category_id is not None:
        statement = statement.where(Expense.category_id == filters.category_id)
    if filters.merchant:
        statement = statement.where(func.lower(Expense.merchant) == filters.merchant.lower())
    if filters.search:
        # autoescape: a % or _ the user types is searched for literally, not used as a wildcard.
        statement = statement.where(
            or_(
                col(Expense.merchant).icontains(filters.search, autoescape=True),
                col(Expense.note).icontains(filters.search, autoescape=True),
            )
        )
    # Newest first: that's how people read a list of expenses.
    statement = statement.order_by(col(Expense.spent_on).desc(), col(Expense.id).desc())
    if filters.limit:
        # The database stops after N rows, rather than sending them all for the caller to cut.
        statement = statement.limit(filters.limit)
    return list(session.exec(statement))


def update(session: Session, expense: Expense, changes: dict[str, Any]) -> Expense:
    for field, value in changes.items():
        setattr(expense, field, value)
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def delete(session: Session, expense: Expense) -> None:
    session.delete(expense)
    session.commit()


def totals_by_category(session: Session, start: date, end: date, currency: str) -> list[tuple[int, int, int]]:
    """(category_id, number of expenses, total paise) for expenses from start up to, not including, end."""
    # The database does the adding up (GROUP BY), instead of loading every row into Python.
    statement = (
        select(Expense.category_id, func.count(col(Expense.id)), func.sum(Expense.amount_minor))
        .where(Expense.spent_on >= start, Expense.spent_on < end, Expense.currency == currency)
        .group_by(col(Expense.category_id))
    )
    return [(category_id, count, total) for category_id, count, total in session.exec(statement)]


def totals_by_month(session: Session, start: date, end: date, currency: str) -> list[tuple[int, int, int, int]]:
    """(year, month, number of expenses, total paise) per month, from start up to, not including, end.

    Months with no expenses are simply absent; the service fills them in.
    """
    # EXTRACT(year/month ...) is standard SQL, so this works on SQLite today and Postgres later
    # (a SQLite-only function like strftime would not).
    year = extract("year", col(Expense.spent_on))
    month = extract("month", col(Expense.spent_on))
    statement = (
        select(year, month, func.count(col(Expense.id)), func.sum(Expense.amount_minor))
        .where(Expense.spent_on >= start, Expense.spent_on < end, Expense.currency == currency)
        .group_by(year, month)
    )
    return [(int(y), int(m), count, total) for y, m, count, total in session.exec(statement)]
