"""The expenses module's contract: the commands, queries and data other code may use.

Schemas check the *shape* of data (types, lengths, at most 2 decimal places). Business rules
(amount > 0, the category must exist) live in domain.py and the command handlers.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.cqrs import Command, Query
from app.core.db import RecordId
from app.core.money import DEFAULT_CURRENCY, CurrencyCode, paise_to_rupees
from app.core.months import YearMonth
from app.modules.categories import CategoryId

MAX_MERCHANT_LENGTH = 100
MAX_NOTE_LENGTH = 500
MAX_SEARCH_LENGTH = 100
# A list returns at most this many expenses by default (newest first), and never more than the max.
DEFAULT_LIST_LIMIT = 100
MAX_LIST_LIMIT = 500
# A trend covers at most two years, so one request can't ask the database for decades of grouping.
DEFAULT_TREND_MONTHS = 6
MAX_TREND_MONTHS = 24


class PaymentMethod(StrEnum):
    # A fixed list, so reports can group by it and typos like "UPI " can't sneak in.
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    OTHER = "other"


# How each method is written for people. The one place these labels live: the assistant's forms use
# them, and the web app gets them through the generated contracts (backend/scripts/export_contracts.py).
PAYMENT_METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CASH: "Cash",
    PaymentMethod.UPI: "UPI",
    PaymentMethod.CARD: "Card",
    PaymentMethod.NETBANKING: "Net banking",
    PaymentMethod.WALLET: "Wallet",
    PaymentMethod.OTHER: "Other",
}

ExpenseId = RecordId
# Every change raises it by one, so "the expense as I saw it" can be checked (optimistic concurrency).
Version = Annotated[int, Field(ge=1)]
# Rupees, as people type them (450.50). The handlers convert to paise for storage.
Amount = Annotated[Decimal, Field(max_digits=12, decimal_places=2, examples=["450.50"])]
Merchant = Annotated[str, Field(min_length=1, max_length=MAX_MERCHANT_LENGTH)]
Note = Annotated[str, Field(max_length=MAX_NOTE_LENGTH)]

# For bodies: strip stray spaces ("Swiggy " would never match a merchant filter). Unknown fields are
# already refused by every Command (a typo like "merchnat" is an error, not a silently ignored change).
_STRIPPED = ConfigDict(str_strip_whitespace=True)


# ---------- data handed out ----------


class ExpenseRead(BaseModel):
    """An expense as callers see it: everything stored, plus the amount in rupees for display."""

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
    version: int

    @computed_field
    @property
    def amount(self) -> Decimal:
        # Worked out from amount_minor every time, so the two can never disagree.
        return paise_to_rupees(self.amount_minor)


class ExpenseList(BaseModel):
    items: list[ExpenseRead]
    # How many match the filters in total; `items` may hold fewer (see ListExpenses.limit).
    total: int


class _Totalled(BaseModel):
    """A total in paise, plus the same total in rupees, worked out from it."""

    total_minor: int

    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)


class CategoryTotal(_Totalled):
    category_id: int
    category_name: str
    expense_count: int


class MonthlySummary(_Totalled):
    month: str = Field(pattern=YearMonth.PATTERN, examples=["2026-11"])
    currency: str
    expense_count: int
    # Biggest spend first.
    by_category: list[CategoryTotal]


class MonthTotal(_Totalled):
    month: str = Field(pattern=YearMonth.PATTERN)
    expense_count: int


class MonthlyTrend(BaseModel):
    currency: str
    # Oldest month first, one entry per month, including months with no spending (total 0),
    # so a chart can draw them without gaps.
    months: list[MonthTotal]


# ---------- commands ----------


class CreateExpense(Command[int]):
    """Record an expense. Returns its id. Also the body of POST /expenses."""

    model_config = _STRIPPED

    amount: Amount
    currency: CurrencyCode = DEFAULT_CURRENCY
    category_id: CategoryId
    merchant: Merchant
    note: Note | None = None
    spent_on: date
    payment_method: PaymentMethod


class ExpenseChanges(BaseModel):
    """The body of PATCH /expenses/{id}: send only the fields you want to change."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    amount: Amount | None = None
    currency: CurrencyCode | None = None
    category_id: CategoryId | None = None
    merchant: Merchant | None = None
    spent_on: date | None = None
    payment_method: PaymentMethod | None = None
    # The one field that can be cleared: send "note": null to remove it.
    note: Note | None = None

    @model_validator(mode="after")
    def only_note_can_be_cleared(self) -> Self:
        # Leaving a field out means "don't change it"; sending null for it would mean "erase it",
        # which only makes sense for the note.
        cleared = sorted(name for name in self.model_fields_set if getattr(self, name) is None and name != "note")
        if cleared:
            raise ValueError(f"{', '.join(cleared)} can't be null; leave a field out to keep it as it is")
        return self


class UpdateExpense(Command[None]):
    expense_id: ExpenseId
    changes: ExpenseChanges


class DeleteExpense(Command[None]):
    expense_id: ExpenseId
    # If given, delete only if the expense is still at this version: what the caller saw and agreed to
    # delete. Checked in the same statement as the delete, so no change can slip in between.
    expected_version: Version | None = None


# ---------- queries ----------


class GetExpense(Query[ExpenseRead]):
    """One expense. Raises NotFoundError if there's no such expense."""

    expense_id: ExpenseId


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

    @model_validator(mode="after")
    def check_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class GetMonthlySummary(Query[MonthlySummary]):
    """One month's total, and the total per category (one currency at a time: totals can't mix them)."""

    month: YearMonth
    currency: CurrencyCode = DEFAULT_CURRENCY


class GetMonthlyTrend(Query[MonthlyTrend]):
    """Totals for the last `months` months, ending with the month that contains `until`."""

    months: int = Field(ge=1, le=MAX_TREND_MONTHS)
    until: date
    currency: CurrencyCode = DEFAULT_CURRENCY
