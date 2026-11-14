"""ListExpenses: one page of expenses, newest first, with optional filters. The query and its handler.

A slice of the expenses module's read side; it never changes anything. module.py registers the handler with the
bus. The database does the filtering and counting (WHERE, COUNT, OFFSET, LIMIT), so only the page shown leaves it,
as ExpenseRead copies in an ExpenseList (models.py). ListExpenses is also GET /expenses's query parameters
(api.py), so its docstring and field descriptions are part of the OpenAPI document: notes are `#` comments.
"""

from datetime import date
from typing import Any, Self

from pydantic import Field, model_validator
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.modules.categories import CategoryId
from app.modules.expenses.models import ExpenseList, ExpenseRead
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, MAX_MERCHANT_LENGTH, MAX_SEARCH_LENGTH


# Asked by GET /expenses (the web app's lists), MCP's list_expenses and its "recent" resource, and seed.py.
# Filters are combined with AND; the handler turns each one given into a WHERE condition.
class ListExpenses(Query[ExpenseList]):
    """Expenses, newest first. All filters are optional; combine as many as you like.

    Also the query parameters of GET /expenses, so unknown parameters (a typo like ?catgory_id=3)
    are an error instead of being silently ignored.
    """

    start_date: date | None = None
    end_date: date | None = None
    category_id: CategoryId | None = None
    # min_length=1: an empty value is an error, not a silent "no filter".
    merchant: str | None = Field(
        default=None, min_length=1, max_length=MAX_MERCHANT_LENGTH, description="Exact merchant name, any letter case"
    )
    search: str | None = Field(
        default=None, min_length=1, max_length=MAX_SEARCH_LENGTH, description="Text to find in the merchant or note"
    )
    limit: int = Field(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT, description="At most this many, newest first")
    offset: int = Field(default=0, ge=0, description="Skip this many first (for the next page)")

    # A start after the end can match nothing, which is almost certainly a mistake: refuse it (a
    # validation error) rather than quietly answer with an empty list.
    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


def _matching(query: ListExpenses) -> list[Any]:
    """The WHERE conditions for a list's filters; list_expenses uses them for both the count and the page."""
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
        # icontains lowercases both sides in the database too (lower(...) LIKE '%' || lower(?) || '%').
        conditions.append(
            or_(
                col(Expense.merchant).icontains(query.search, autoescape=True),
                col(Expense.note).icontains(query.search, autoescape=True),
            )
        )
    return conditions


def list_expenses(ctx: Context, query: ListExpenses) -> ExpenseList:
    """One page of the expenses that match the filters, newest first, plus how many match in all.

    Two statements with the same conditions: COUNT(*) for the total, then the page itself with OFFSET
    and LIMIT, so only the rows shown leave the database.
    """
    conditions = _matching(query)
    total = ctx.session.exec(select(func.count()).select_from(Expense).where(*conditions)).one()
    rows = ctx.session.exec(
        select(Expense)
        .where(*conditions)
        # Newest first: that's how people read a list of expenses.
        # The id breaks ties between expenses on the same day, so pages never overlap or skip a row.
        .order_by(col(Expense.spent_on).desc(), col(Expense.id).desc())
        .offset(query.offset)
        .limit(query.limit)
    )
    return ExpenseList(items=[ExpenseRead.model_validate(row) for row in rows], total=total)
