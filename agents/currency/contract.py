"""The currency agent's wire contract: the skill's id, what a request carries, and the shape of the answer.

Contract layer of the currency agent. The executor reads requests and writes answers with it; the card names the
skill. A client sends one data part (ConversionRequest) or one line of text ("4 USD to INR", "4.50 usd in inr on
2026-11-19", parsed by parse_text), and reads one data artifact, `conversion` (ConversionAnswer). The backend's
expenses module asks for 1 unit of a currency in INR on an expense's date, and works out the amount itself (D204).

Amounts and rates travel as decimal strings: a JSON number could be read as a float, and money is never a float.
"""

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.core.money import CurrencyCode

SKILL_ID = "convert_currency"
ARTIFACT_NAME = "conversion"
JSON_MEDIA_TYPE = "application/json"
TEXT_MEDIA_TYPE = "text/plain"
# An amount as the request writes it: at most 12 digits, then at most 2 decimals ("4", "450.50").
AmountText = Annotated[str, StringConstraints(pattern=r"^\d{1,12}(\.\d{1,2})?$")]
# One line asking for a conversion: an amount, a currency, "to" or "in", a currency, and optionally "on" a date.
TEXT_REQUEST = re.compile(
    r"^\s*(\d{1,12}(?:\.\d{1,2})?)\s+([A-Za-z]{3})\s+(?:to|in)\s+([A-Za-z]{3})"
    r"(?:\s+on\s+(\d{4}-\d{2}-\d{2}))?\s*\??\s*$"
)


# The request's data part. Unknown fields are refused, so a client can't believe it sent something that's ignored.
class ConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: AmountText
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    # The day the rate is for; today if left out. A day after today is read as today.
    on: date | None = None


# The `conversion` artifact's data: the request as understood, the rate used and its day, the converted amount (rounded
# half up to 2 decimals: core.money.convert_minor) and where the rate came from.
class ConversionAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: str
    from_currency: str
    to_currency: str
    rate: str
    rate_date: date
    converted: str
    source: str


def parse_text(line: str) -> ConversionRequest | None:
    """The ConversionRequest a line of text asks for ("4 USD to INR on 2026-11-19"), or None if it isn't one."""
    match = TEXT_REQUEST.match(line)
    if match is None:
        return None
    amount, source, target, on = match.groups()
    return ConversionRequest.model_validate(
        {"amount": amount, "from_currency": source.upper(), "to_currency": target.upper(), "on": on}
    )
