from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel

from app.core.money import DEFAULT_CURRENCY


class Expense(SQLModel, table=True):
    """The expenses table. Private to this module: other modules never import it."""

    id: int | None = Field(default=None, primary_key=True)
    # Whole paise, never a float of rupees: 450.50 rupees is stored as 45050.
    amount_minor: int
    currency: str = Field(default=DEFAULT_CURRENCY, max_length=3)
    # Just the id, with no database foreign key: the categories table belongs to another
    # module, so the link is checked through that module's service, not by the database.
    category_id: int = Field(index=True)
    merchant: str = Field(max_length=100)
    note: str | None = Field(default=None, max_length=500)
    # Indexed because "expenses this month" will be the most common query.
    spent_on: date = Field(index=True)
    payment_method: str = Field(max_length=20)
    # Always UTC; converting to the user's time zone is the frontend's job.
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
