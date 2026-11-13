from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import DEFAULT_CURRENCY


class PaymentMethod(StrEnum):
    # A fixed list, so reports can group by it and typos like "UPI " can't sneak in.
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    OTHER = "other"


class ExpenseCreate(BaseModel):
    """What it takes to record an expense."""

    amount_minor: int = Field(gt=0, description="Amount in paise: 450.50 rupees is 45050")
    currency: str = Field(default=DEFAULT_CURRENCY, pattern=r"^[A-Z]{3}$")
    category_id: int
    merchant: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)
    spent_on: date
    payment_method: PaymentMethod


class ExpenseRead(ExpenseCreate):
    """What other modules get back: a frozen copy, not the table row."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    created_at: datetime
