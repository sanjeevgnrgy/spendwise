"""Which month a request is about: the months the expenses cover, and the month a person's reply names.

Domain logic of the insights agent, pure functions. The executor asks which month to analyse when a request names
none and its expenses span several (INPUT_REQUIRED); the person's reply comes back as a line of text, read here
without a model: "2026-11", a month's name in English or Hindi (with or without a year), "this month" or "last
month". A reply that names no month is asked about again (D205).
"""

import re
from datetime import date

from app.core.months import YearMonth
from insights.contract import ExpenseRow

# A month's name, as a person might write it, to its number. English (full and short) and Hindi.
MONTH_NAMES: dict[str, int] = {
    **{
        name.lower(): number
        for number, name in enumerate(
            [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            start=1,
        )
    },
    **{
        name: number
        for number, name in enumerate(
            ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
        )
    },
    "sept": 9,
    **{
        name: number
        for number, name in enumerate(
            ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"], start=1
        )
    },
    "फरवरी": 2,
}
THIS_MONTH = ("this month", "current month", "इस महीने", "यह महीना")
LAST_MONTH = ("last month", "previous month", "पिछले महीने", "पिछला महीना")
YEAR_MONTH = re.compile(r"\b((?:19|20)\d{2})-(0[1-9]|1[0-2])\b")
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
# Words are split on spaces and punctuation, not \w: Hindi vowel signs aren't "word" characters to a regex.
SEPARATORS = re.compile(r"[\s,.!?;:()\"']+")


def months_in(expenses: list[ExpenseRow]) -> list[YearMonth]:
    """The months the expenses fall in, oldest first."""
    return sorted({YearMonth.of(row.spent_on) for row in expenses})


def month_in_reply(reply: str, today: date) -> YearMonth | None:
    """The month a person's reply names, or None. A name without a year is the latest such month up to today's."""
    text = reply.strip().lower()
    if match := YEAR_MONTH.search(text):
        return YearMonth(int(match.group(1)), int(match.group(2)))
    current = YearMonth.of(today)
    if any(phrase in text for phrase in THIS_MONTH):
        return current
    if any(phrase in text for phrase in LAST_MONTH):
        return current.shift(-1)
    number = next((MONTH_NAMES[word] for word in SEPARATORS.split(text) if word in MONTH_NAMES), None)
    if number is None:
        return None
    if year := YEAR.search(text):
        return YearMonth(int(year.group(1)), number)
    # "November" in December 2026 is November 2026; in October 2026, November 2025.
    year_now = today.year if number <= today.month else today.year - 1
    return YearMonth(year_now, number)
