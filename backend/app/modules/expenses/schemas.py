from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.db import MAX_ID
from app.core.money import DEFAULT_CURRENCY, paise_to_rupees

# These schemas check the *shape* of data (types, lengths, at most 2 decimal places).
# Business rules (amount > 0, the category must exist) live in service.py.

# A month as YYYY-MM, for years 1900-2099: wide enough for any real expense, and it keeps
# date() away from years it can't represent (0000 or 9999-12's "next month" would be a 500).
MONTH_PATTERN = r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"

# For bodies: strip stray spaces ("Swiggy " would never match a merchant filter), and reject
# unknown fields, so a typo like "merchnat" is an error instead of a silently ignored change.
_STRICT_INPUT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PaymentMethod(StrEnum):
    # A fixed list, so reports can group by it and typos like "UPI " can't sneak in.
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    OTHER = "other"


class ExpenseCreate(BaseModel):
    """What a caller sends to record an expense. No id or created_at: the server sets those."""

    model_config = _STRICT_INPUT

    # Rupees, as people type them (450.50). The service converts to paise for storage.
    amount: Decimal = Field(max_digits=12, decimal_places=2, examples=["450.50"])
    currency: str = Field(default=DEFAULT_CURRENCY, pattern=r"^[A-Z]{3}$")
    category_id: int = Field(ge=1, le=MAX_ID)
    merchant: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)
    spent_on: date
    payment_method: PaymentMethod


class ExpenseUpdate(BaseModel):
    """PATCH body: send only the fields you want to change."""

    model_config = _STRICT_INPUT

    # These default to None but aren't typed "| None": leaving a field out means
    # "don't change it", while sending null for it fails validation (422).
    amount: Decimal = Field(default=None, max_digits=12, decimal_places=2)
    currency: str = Field(default=None, pattern=r"^[A-Z]{3}$")
    category_id: int = Field(default=None, ge=1, le=MAX_ID)
    merchant: str = Field(default=None, min_length=1, max_length=100)
    spent_on: date = Field(default=None)
    payment_method: PaymentMethod = Field(default=None)
    # The one field that can be cleared: send "note": null to remove it.
    note: str | None = Field(default=None, max_length=500)


class ExpenseRead(BaseModel):
    """What callers get back: everything stored, plus the amount in rupees for display."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    # Paise: the exact stored value, safe for arithmetic.
    amount_minor: int
    currency: str
    category_id: int
    merchant: str
    note: str | None
    spent_on: date
    payment_method: PaymentMethod
    created_at: datetime

    @computed_field
    @property
    def amount(self) -> Decimal:
        # Worked out from amount_minor every time, so the two can never disagree.
        return paise_to_rupees(self.amount_minor)


class ExpenseFilters(BaseModel):
    """Query parameters for GET /expenses. All optional; combine as many as you like."""

    # Reject unknown parameters, so a typo like ?catgory_id=3 is an error instead of silently ignored.
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None
    category_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    # min_length=1 like `search`: an empty value is an error, not a silent "no filter".
    merchant: str | None = Field(
        default=None, min_length=1, max_length=100, description="Exact merchant name, any letter case"
    )
    search: str | None = Field(
        default=None, min_length=1, max_length=100, description="Text to find in the merchant or note"
    )
    # Return at most this many (newest first). Lets the Dashboard ask for "the 5 latest" without
    # downloading every expense.
    limit: int | None = Field(default=None, ge=1, le=500, description="At most this many expenses, newest first")

    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class CategoryTotal(BaseModel):
    category_id: int
    category_name: str
    expense_count: int
    total_minor: int

    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)


class MonthlySummary(BaseModel):
    month: str
    currency: str
    expense_count: int
    total_minor: int
    # Biggest spend first.
    by_category: list[CategoryTotal]

    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)


class MonthTotal(BaseModel):
    month: str  # "YYYY-MM"
    expense_count: int
    total_minor: int

    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)


class MonthlyTrend(BaseModel):
    currency: str
    # Oldest month first, one entry per month, including months with no spending (total 0),
    # so a chart can draw them without gaps.
    months: list[MonthTotal]
