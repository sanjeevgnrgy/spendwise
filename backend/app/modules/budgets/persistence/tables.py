"""The budgets module's table: `budget`.

Private to this module: only its handlers (the command slices through repository.py, and the query slices) read or
write it. Other modules ask through the contract (the package's __init__.py), and the composition root hands TABLES to
the migrations. The table is created and changed by Alembic migrations (0010), never by the app.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, text
from sqlmodel import Field, SQLModel

# One budget per person and category, and one overall budget (no category) per person. A unique index on
# (owner_id, category_id) covers the first; SQL treats NULLs as distinct, so the overall budget needs a partial
# unique index of its own, on owner_id where category_id is null.
OWNER_CATEGORY_INDEX = "uq_budget_owner_id_category_id"
OWNER_OVERALL_INDEX = "uq_budget_owner_id_overall"
OVERALL_ROWS = text("category_id IS NULL")


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class Budget(SQLModel, table=True):
    """The budgets table. Private to this module: other modules never import it."""

    __table_args__ = (
        Index(OWNER_CATEGORY_INDEX, "owner_id", "category_id", unique=True),
        Index(OWNER_OVERALL_INDEX, "owner_id", unique=True, sqlite_where=OVERALL_ROWS, postgresql_where=OVERALL_ROWS),
    )

    # None until the row is inserted; the database assigns it (repository.save's flush).
    id: int | None = Field(default=None, primary_key=True)
    # Whose budget it is (core.ids.UserId), a plain id with no foreign key: the users table is the accounts module's.
    # Every read and change filters on it (D190).
    owner_id: int
    # The category the budget is for, or None for the overall budget (the whole month's spending). Just the id, with
    # no foreign key: categories belong to another module, checked through its queries.
    category_id: int | None = None
    # The monthly limit, in whole paise (INR): the same every month until it's changed.
    limit_minor: int
    # When the limit was last set, in UTC, from the app's clock.
    updated_at: datetime = Field(sa_type=DateTime(timezone=True))


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (Budget,)
