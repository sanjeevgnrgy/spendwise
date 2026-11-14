"""The expenses module's contract: the commands, queries and data other code may use.

Schemas check the *shape* of data (types, lengths, at most 2 decimal places). Business rules
(amount > 0, the category must exist) live in domain.py and the command handlers.

What's here: the limits, PaymentMethod and its labels, the data handed out (ExpenseRead, ExpenseList,
the summary and trend totals), three commands (CreateExpense, UpdateExpense, DeleteExpense) and four
queries (GetExpense, ListExpenses, GetMonthlySummary, GetMonthlyTrend). Many of these are also REST
bodies, query parameters or responses (api.py), and the MCP server's results build on them, so their
docstrings and field descriptions are part of the published schemas. Notes for people reading the code
are `#` comments instead.

Money: callers send and get rupees as a Decimal (`amount`, `total`); the table keeps whole paise
(`amount_minor`, `total_minor`), never a float.

Used by: the MCP server (every command and query), the assistant (PaymentMethod and its labels),
seed.py, and scripts/export_contracts.py (the labels and limits, for the web app).
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.cqrs import Command, Query
from app.core.ids import RecordId
from app.core.money import DEFAULT_CURRENCY, CurrencyCode, paise_to_rupees
from app.core.months import YearMonth
from app.modules.categories import CategoryId

# Text limits. The merchant and note limits are also the table's column lengths (tables.py).
MAX_MERCHANT_LENGTH = 100
MAX_NOTE_LENGTH = 500
MAX_SEARCH_LENGTH = 100
# A list returns at most this many expenses by default (newest first), and never more than the max.
DEFAULT_LIST_LIMIT = 100
MAX_LIST_LIMIT = 500
# A trend covers at most two years, so one request can't ask the database for decades of grouping.
DEFAULT_TREND_MONTHS = 6
MAX_TREND_MONTHS = 24


# How an expense was paid. The value ("upi") is what's stored, sent in JSON and accepted from callers.
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
# At most 12 digits, 2 of them after the point: a fraction of a paisa (450.505) is refused, never rounded
# away.
Amount = Annotated[Decimal, Field(max_digits=12, decimal_places=2, examples=["450.50"])]
Merchant = Annotated[str, Field(min_length=1, max_length=MAX_MERCHANT_LENGTH)]
Note = Annotated[str, Field(max_length=MAX_NOTE_LENGTH)]

# For bodies: strip stray spaces ("Swiggy " would never match a merchant filter). Unknown fields are
# already refused by every Command (a typo like "merchnat" is an error, not a silently ignored change).
_STRIPPED = ConfigDict(str_strip_whitespace=True)


# ---------- data handed out ----------


# What GetExpense and ListExpenses return, and the REST API's expense object. Built straight from a table
# row (from_attributes); frozen, so nobody can change stored data through it.
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

    # A computed field: sent in the JSON (and listed in the schema) as "amount", never stored. No
    # docstring on it: Pydantic would publish that as the field's description.
    @computed_field
    @property
    def amount(self) -> Decimal:
        # Worked out from amount_minor every time, so the two can never disagree.
        return paise_to_rupees(self.amount_minor)


# ListExpenses's answer: one page of expenses, plus how many match in all, so a caller can page through
# them or say "showing 50 of 120".
class ExpenseList(BaseModel):
    items: list[ExpenseRead]
    # How many match the filters in total; `items` may hold fewer (see ListExpenses.limit).
    total: int


# The shared base of every total below. Private to this file (the leading underscore).
class _Totalled(BaseModel):
    """A total in paise, plus the same total in rupees, worked out from it."""

    total_minor: int

    # Rupees for display, computed from total_minor so the two never disagree. (A comment, not a
    # docstring: a computed field's docstring becomes its description in the schema.)
    @computed_field
    @property
    def total(self) -> Decimal:
        return paise_to_rupees(self.total_minor)


# One category's share of a month, in MonthlySummary.by_category. category_name is "Unknown"
# (categories.UNKNOWN_CATEGORY) if the category no longer exists.
class CategoryTotal(_Totalled):
    category_id: int
    category_name: str
    expense_count: int


# GetMonthlySummary's answer (GET /summary): one month's total in one currency, and the total for each
# category that had spending. The month is written as "YYYY-MM" text.
class MonthlySummary(_Totalled):
    month: str = Field(pattern=YearMonth.PATTERN, examples=["2026-11"])
    currency: str
    expense_count: int
    # Biggest spend first.
    by_category: list[CategoryTotal]


# One month of a trend: its total and how many expenses it had. MCP's get_summary also uses it for the
# previous month.
class MonthTotal(_Totalled):
    month: str = Field(pattern=YearMonth.PATTERN)
    expense_count: int


# GetMonthlyTrend's answer (GET /summary/trend), for the Dashboard's chart.
class MonthlyTrend(BaseModel):
    currency: str
    # Oldest month first, one entry per month, including months with no spending (total 0),
    # so a chart can draw them without gaps.
    months: list[MonthTotal]


# ---------- commands ----------


# Sent by POST /expenses, MCP's add_expense and seed.py. Beyond the shape checked here, the handler
# refuses an amount <= 0 or a category that doesn't exist, with a BusinessRuleError
# (commands.create_expense).
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


# What to change in an expense: UpdateExpense carries it, and PATCH /expenses/{id} takes it as the body.
# Only a part of a command, not a Message itself, so it sets frozen and extra="forbid" on its own. Every
# field defaults to None, so the validator below tells "left out" apart from "sent as null".
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

    # Refuses null for any field but the note. The ValueError becomes a validation error that names the
    # fields (a 422 on REST). model_fields_set holds only the fields the caller actually sent, so fields
    # left out (None by default) pass.
    @model_validator(mode="after")
    def only_note_can_be_cleared(self) -> Self:
        # Leaving a field out means "don't change it"; sending null for it would mean "erase it",
        # which only makes sense for the note.
        cleared = sorted(name for name in self.model_fields_set if getattr(self, name) is None and name != "note")
        if cleared:
            raise ValueError(f"{', '.join(cleared)} can't be null; leave a field out to keep it as it is")
        return self


# Change some fields of one expense (PATCH /expenses/{id}, MCP's update_expense). The handler raises
# NotFoundError for a missing expense and BusinessRuleError for an amount <= 0 or an unknown category,
# and raises the version by one. There's no expected_version: an update applies to whatever is stored
# (last write wins); only deletes check the version.
class UpdateExpense(Command[None]):
    expense_id: ExpenseId
    changes: ExpenseChanges


# Remove one expense for good. Raises NotFoundError if it doesn't exist, and BusinessRuleError if
# expected_version was given and no longer matches (repository.remove). The REST route deletes without
# a version; the assistant's Approve button passes the version its card showed.
class DeleteExpense(Command[None]):
    expense_id: ExpenseId
    # If given, delete only if the expense is still at this version: what the caller saw and agreed to
    # delete. Checked in the same statement as the delete, so no change can slip in between.
    expected_version: Version | None = None


# ---------- queries ----------


# Routes ask it after a command to answer with the saved expense; the MCP tools ask it to show one.
class GetExpense(Query[ExpenseRead]):
    """One expense. Raises NotFoundError if there's no such expense."""

    expense_id: ExpenseId


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


# Asked by GET /summary and by MCP's get_summary (for the month asked about and the one before). The
# month is a YearMonth value, so the handler can work out where it ends.
class GetMonthlySummary(Query[MonthlySummary]):
    """One month's total, and the total per category (one currency at a time: totals can't mix them)."""

    month: YearMonth
    currency: CurrencyCode = DEFAULT_CURRENCY


# Asked by GET /summary/trend, with `until` set to the clock's today.
class GetMonthlyTrend(Query[MonthlyTrend]):
    """Totals for the last `months` months, ending with the month that contains `until`."""

    months: int = Field(ge=1, le=MAX_TREND_MONTHS)
    until: date
    currency: CurrencyCode = DEFAULT_CURRENCY
