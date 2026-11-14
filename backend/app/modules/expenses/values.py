"""The expenses module's shared values: limits, PaymentMethod, the id and field types.

Schemas check the *shape* of data (types, lengths, at most 2 decimal places). Business rules
(amount > 0, the category must exist) live in domain/rules.py and the command handlers.

Money: callers send and get rupees as a Decimal (`amount`, `total`); the table keeps whole paise
(`amount_minor`, `total_minor`), never a float.

Part of the module's contract layer, used by its slices (commands/, queries/), models.py, api.py and its table
(persistence/tables.py); this file imports no other file of the module. __init__.py exports MAX_LIST_LIMIT,
PaymentMethod and ExpenseId. Each method's label, in every language, is in i18n/ (payment_method_label); the assistant
uses both, and scripts/export_contracts.py reads the labels and limits for the web app.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import Field

from app.core.ids import RecordId

# Text limits. The merchant and note limits are also the table's column lengths (persistence/tables.py).
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


ExpenseId = RecordId
# Every change raises it by one, so "the expense as I saw it" can be checked (optimistic concurrency).
Version = Annotated[int, Field(ge=1)]
# Rupees, as people type them (450.50). The handlers convert to paise for storage.
# At most 12 digits, 2 of them after the point: a fraction of a paisa (450.505) is refused, never rounded
# away.
Amount = Annotated[Decimal, Field(max_digits=12, decimal_places=2, examples=["450.50"])]
Merchant = Annotated[str, Field(min_length=1, max_length=MAX_MERCHANT_LENGTH)]
Note = Annotated[str, Field(max_length=MAX_NOTE_LENGTH)]
