"""The expenses module's table: `expense`.

Private to this module: only its handlers (the command slices through repository.py, and the query slices) read
or write it. Other modules ask through the contract (the package's __init__.py), and the composition root hands
TABLES to the migrations. The table itself is created and changed by Alembic migrations, never by the app.
"""

from datetime import date, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.core.money import DEFAULT_CURRENCY
from app.modules.expenses.values import MAX_MERCHANT_LENGTH, MAX_NOTE_LENGTH

# Column lengths. An ISO 4217 currency code is three letters; the longest payment method today
# ("netbanking") is 10 characters.
CURRENCY_LENGTH = 3
PAYMENT_METHOD_LENGTH = 20


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class Expense(SQLModel, table=True):
    """The expenses table. Private to this module: other modules never import it."""

    # None until the row is inserted; the database assigns it (see repository.add's flush).
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
    # A PaymentMethod value ("upi"), stored as plain text; the contract's enum checks it on the way in.
    payment_method: str = Field(max_length=PAYMENT_METHOD_LENGTH)
    # Always UTC, stored with its time zone; converting to the user's time zone is the frontend's job.
    # create_expense sets it from the app's injected clock. No default on purpose: a row made without it
    # fails at the INSERT (the column is NOT NULL) instead of quietly getting the server's own time.
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
    # Raised by one on every change (optimistic concurrency): see DeleteExpense.expected_version.
    version: int = Field(default=1)


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (Expense,)
