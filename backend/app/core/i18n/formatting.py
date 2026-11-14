"""Money, days and months written for people, in a language's conventions (core layer).

Babel's CLDR data, the same data the browser's Intl uses, so a card the server builds and a page the web app draws
write the same value the same way (₹1,25,000.50, "13 नव॰ 2026", "नवंबर 2026"). Used by the assistant's cards and by
core/money.py's format_money.
"""

from datetime import date
from decimal import Decimal

from babel.dates import format_date, format_skeleton
from babel.numbers import format_currency

from app.core.i18n.languages import DEFAULT_LANGUAGE, LANGUAGES, Language

# CLDR skeletons: what to show, each locale choosing order and punctuation (as Intl's options do in the web app).
DAY_SKELETON = "yMMMd"  # 13 Nov 2026
MONTH_AND_YEAR_SKELETON = "yMMMM"  # November 2026
# A month's full name alone ("November"), as Intl's { month: "long" } writes it. A pattern, not a skeleton: CLDR has
# no "MMMM" skeleton, and Babel matches it to "MMM" without widening it, which would write "Nov".
MONTH_NAME_PATTERN = "LLLL"


def _locale(language: Language) -> str:
    return LANGUAGES[language].locale


def format_currency_amount(amount: Decimal, currency: str, language: Language = DEFAULT_LANGUAGE) -> str:
    """An amount in its currency, as `language` writes it: "₹1,25,000.50"; "$1,250.50" for USD."""
    return format_currency(amount, currency, locale=_locale(language))


def format_day(day: date, language: Language = DEFAULT_LANGUAGE) -> str:
    """A day: "13 Nov 2026" in English, "13 नव॰ 2026" in Hindi."""
    return format_skeleton(DAY_SKELETON, day, locale=_locale(language))


def format_month(month: date, language: Language = DEFAULT_LANGUAGE, *, with_year: bool = True) -> str:
    """The month a day falls in: "November 2026", or "November" without the year."""
    if with_year:
        return format_skeleton(MONTH_AND_YEAR_SKELETON, month, locale=_locale(language))
    return format_date(month, MONTH_NAME_PATTERN, locale=_locale(language))
