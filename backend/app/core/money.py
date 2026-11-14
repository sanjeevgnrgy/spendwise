"""Money: rupees <-> paise, currency codes, and writing an amount for people (core infrastructure).

Amounts are stored and added up as whole paise (integers), and converted through Decimal, never float, so
no rounding error can creep into a total. Used by the expenses module (contracts, handlers, table), the MCP
server and the assistant's cards, seed.py, and the export script (which hands the currency values to the
web app, whose formatMoney matches format_money).
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

DEFAULT_CURRENCY = "INR"
PAISE_PER_RUPEE = 100
# An ISO 4217 code in capitals ("INR", "USD"). Lowercase "inr" is refused rather than quietly
# matching nothing, which would show a 0 total.
CURRENCY_PATTERN = r"^[A-Z]{3}$"
CurrencyCode = Annotated[str, Field(pattern=CURRENCY_PATTERN, examples=[DEFAULT_CURRENCY])]
# Currencies shown with a symbol in front ("₹2,340.00"); any other is shown with its code after it.
CURRENCY_SYMBOLS = {"INR": "₹"}


def rupees_to_paise(rupees: Decimal | int | str) -> int:
    """'450.50' -> 45050."""
    # Decimal, never float: floats can't hold most decimal fractions exactly (0.1 + 0.2 != 0.3).
    paise = Decimal(str(rupees)) * PAISE_PER_RUPEE
    # Refuse fractions of a paisa rather than silently rounding money away.
    if paise != paise.to_integral_value():
        raise ValueError(f"{rupees} rupees has more than 2 decimal places")
    return int(paise)


def paise_to_rupees(paise: int) -> Decimal:
    """45050 -> Decimal('450.50')."""
    # scaleb(-2) shifts the decimal point two places and keeps both digits ("450.50", not "450.5").
    return Decimal(paise).scaleb(-2)


def _indian_grouping(whole: str) -> str:
    """Commas in a string of digits, the Indian way: '12345678' -> '1,23,45,678'."""
    # India groups the last three digits, then pairs: 12345678 -> 1,23,45,678 (the web's Intl "en-IN" does the same).
    if len(whole) <= 3:
        return whole
    head, last_three = whole[:-3], whole[-3:]
    pairs = [head[max(i - 2, 0) : i] for i in range(len(head), 0, -2)]
    return ",".join(reversed(pairs)) + "," + last_three


def format_money(amount: Decimal, currency: str) -> str:
    """Decimal('125000.5'), 'INR' -> '₹1,25,000.50'; 'USD' -> '1,25,000.50 USD'. Matches the web app's formatMoney."""
    sign = "-" if amount < 0 else ""
    whole, _, fraction = f"{abs(amount):.2f}".partition(".")
    number = f"{sign}{_indian_grouping(whole)}.{fraction}"
    symbol = CURRENCY_SYMBOLS.get(currency)
    return f"{symbol}{number}" if symbol else f"{number} {currency}"
