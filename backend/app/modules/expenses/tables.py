from datetime import UTC, date, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.core.money import DEFAULT_CURRENCY
from app.modules.expenses.contracts import MAX_MERCHANT_LENGTH, MAX_NOTE_LENGTH

CURRENCY_LENGTH = 3
PAYMENT_METHOD_LENGTH = 20


class Expense(SQLModel, table=True):
    """The expenses table. Private to this module: other modules never import it."""

    id: int | None = Field(default=None, primary_key=True)
    # Whole paise, never a float of rupees: 450.50 rupees is stored as 45050.
    amount_minor: int
    currency: str = Field(default=DEFAULT_CURRENCY, max_length=CURRENCY_LENGTH)
    # Just the id, with no database foreign key: the categories table belongs to another
    # module, so the link is checked through that module's queries, not by the database.
    category_id: int = Field(index=True)
    merchant: str = Field(max_length=MAX_MERCHANT_LENGTH)
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)
    # Indexed because "expenses this month" is the most common query.
    spent_on: date = Field(index=True)
    payment_method: str = Field(max_length=PAYMENT_METHOD_LENGTH)
    # Always UTC, stored with its time zone; converting to the user's time zone is the frontend's job.
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))
    # Raised by one on every change (optimistic concurrency): see DeleteExpense.expected_version.
    version: int = Field(default=1)


TABLES = (Expense,)
