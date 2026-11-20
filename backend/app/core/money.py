"""Money: rupees <-> paise, currency codes, and writing an amount for people (core layer).

Amounts are stored and added up as whole paise (integers), and converted through Decimal, never float, so no rounding
error can creep into a total. convert_minor is the one rule for an amount in another currency: the expenses module
stores both (Phase 25), and the currency agent (agents/currency) answers with the same arithmetic. Used by the expenses
module (contracts, handlers, table), the MCP server and the assistant's cards, seed.py, and the export script (which
hands the currency values to the web app, whose formatMoney writes amounts the same way, from the same CLDR data).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import Field

from app.core.i18n import DEFAULT_LANGUAGE, Language, format_currency_amount

DEFAULT_CURRENCY = "INR"
# The currency every expense is also stored in, and every total is added up in (D204): the default one.
BASE_CURRENCY = DEFAULT_CURRENCY
PAISE_PER_RUPEE = 100
# An ISO 4217 code in capitals ("INR", "USD"). Lowercase "inr" is refused rather than quietly
# matching nothing, which would show a 0 total.
CURRENCY_PATTERN = r"^[A-Z]{3}$"
CurrencyCode = Annotated[str, Field(pattern=CURRENCY_PATTERN, examples=[DEFAULT_CURRENCY])]
# A currency's symbol where the app shows one on its own, as a chart's unit ("₹").
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


def format_money(amount: Decimal, currency: str, language: Language = DEFAULT_LANGUAGE) -> str:
    """Decimal('125000.5'), 'INR' -> '₹1,25,000.50'; 'USD' -> '$1,250.50': the currency's CLDR format in the
    language's locale (India's digit grouping for English and Hindi). Matches the web app's formatMoney."""
    return format_currency_amount(amount, currency, language)


def convert_minor(amount_minor: int, rate: Decimal) -> int:
    """An amount in minor units (cents, paise...) times `rate`, in the other currency's minor units: 400 cents at
    84.5 -> 33800 paise. Rounded half up to a whole minor unit, the one place a conversion rounds (D204)."""
    return int((Decimal(amount_minor) * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
