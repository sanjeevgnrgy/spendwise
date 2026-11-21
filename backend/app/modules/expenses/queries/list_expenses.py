"""ListExpenses: one page of a person's expenses, newest first, with optional filters. The query and its handler.

A slice of the expenses module's read side; it never changes anything. module.py registers the handler with the
bus. The database does the filtering and counting (WHERE, COUNT, OFFSET, LIMIT), so only the page shown leaves it,
as ExpenseRead copies in an ExpenseList (models.py). ExpenseFilters is also GET /expenses's query parameters
(api.py), so its docstring and field descriptions are part of the OpenAPI document: notes are `#` comments.
"""

from datetime import date
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, or_
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.modules.categories import CategoryId
from app.modules.expenses.models import ExpenseList, ExpenseRead
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, MAX_MERCHANT_LENGTH, MAX_SEARCH_LENGTH


# Which expenses, and which page: GET /expenses's query parameters, MCP's list_expenses arguments (translated) and
# its "recent" resource. Combined with AND. Not a message: it has no owner, which the server adds (ListExpenses), so
# a query string can't name someone else (an ?owner_id= is an unknown parameter: a 422, like a typo).
class ExpenseFilters(BaseModel):
    """Expenses, newest first. All filters are optional; combine as many as you like.

    Also the query parameters of GET /expenses, so unknown parameters (a typo like ?catgory_id=3)
    are an error instead of being silently ignored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

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
    limit: int = Field(
        default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT, description="At most this many, newest first"
    )
    offset: int = Field(default=0, ge=0, description="Skip this many first (for the next page)")

    # A start after the end can match nothing, which is almost certainly a mistake: refuse it (a
    # validation error) rather than quietly answer with an empty list.
    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


# Asked by GET /expenses (the web app's lists), MCP's list_expenses and its "recent" resource, and seed.py: always one
# person's expenses (D190).
class ListExpenses(Query[ExpenseList]):
    """The owner's expenses that match the filters, newest first."""

    owner_id: UserId
    filters: ExpenseFilters = ExpenseFilters()


def _matching(owner_id: int, filters: ExpenseFilters) -> list[Any]:
    """The WHERE conditions for the owner and a list's filters; list_expenses uses them for both the count and the
    page."""
    # The owner always; each filter only when it was given, so no filters means "all of theirs".
    conditions: list[Any] = [Expense.owner_id == owner_id]
    if filters.start_date:
        conditions.append(Expense.spent_on >= filters.start_date)
    if filters.end_date:
        conditions.append(Expense.spent_on <= filters.end_date)
    if filters.category_id is not None:
        conditions.append(Expense.category_id == filters.category_id)
    if filters.merchant:
        # The database lowercases both sides. Python's .lower() handles letters like "É" that SQLite's
        # lower() leaves alone, so mixing the two would make "CAFÉ" never match itself.
        conditions.append(func.lower(Expense.merchant) == func.lower(filters.merchant))
    if filters.search:
        # autoescape: a % or _ the user types is searched for literally, not used as a wildcard.
        # icontains lowercases both sides in the database too (lower(...) LIKE '%' || lower(?) || '%').
        conditions.append(
            or_(
                col(Expense.merchant).icontains(filters.search, autoescape=True),
                col(Expense.note).icontains(filters.search, autoescape=True),
            )
        )
    return conditions


def list_expenses(ctx: Context, query: ListExpenses) -> ExpenseList:
    """One page of the owner's expenses that match the filters, newest first, plus how many match in all.

    Two statements with the same conditions: COUNT(*) for the total, then the page itself with OFFSET
    and LIMIT, so only the rows shown leave the database.
    """
    filters = query.filters
    conditions = _matching(query.owner_id, filters)
    total = ctx.session.exec(select(func.count()).select_from(Expense).where(*conditions)).one()
    rows = ctx.session.exec(
        select(Expense)
        .where(*conditions)
        # Newest first: that's how people read a list of expenses.
        # The id breaks ties between expenses on the same day, so pages never overlap or skip a row.
        .order_by(col(Expense.spent_on).desc(), col(Expense.id).desc())
        .offset(filters.offset)
        .limit(filters.limit)
    )
    return ExpenseList(items=[ExpenseRead.model_validate(row) for row in rows], total=total)
