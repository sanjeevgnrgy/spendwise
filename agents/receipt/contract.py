"""The receipt agent's wire contract: the skill's id, what a request carries, and the shape of the answer.

Contract layer of the receipt agent. The executor reads requests and writes answers with it, the reader asks the
model for ReceiptExtraction, and the card names the skill and the media types. A client agent (the assistant,
Phase 24 part 2) sends one file part and one data part (ReadingRequest) and reads one data artifact
(ReceiptExtraction).

The agent decides nothing about the person's data: the client sends the categories and payment methods it may
choose from, and today's date, so each is defined once, in the monolith.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.llm import DecimalText

# The one skill the agent offers (its Agent Card lists it), and the name of the artifact it answers with.
SKILL_ID = "extract_receipt"
ARTIFACT_NAME = "receipt_extraction"
# The request's data part and the answer's artifact are JSON.
JSON_MEDIA_TYPE = "application/json"


# The kinds of file the agent reads: a phone's photos and PDFs. The same list as the monolith's uploads accept
# (receipts.ReceiptMediaType); the agent states its own, because it's this service's contract and it checks it.
class ReceiptMediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    PDF = "application/pdf"


# The largest file read: 5 MB, as for uploads. A larger request body is refused before it's parsed (the agent kit's
# gate, agent_kit/http.py).
BYTES_PER_MB = 1024 * 1024
MAX_RECEIPT_MB = 5
MAX_RECEIPT_BYTES = MAX_RECEIPT_MB * BYTES_PER_MB
# How many receipt lines the model may list: a long supermarket bill fits, and the answer stays bounded.
MAX_LINE_ITEMS = 50
# Bounds on the choices a client sends (a category name is at most 50 characters in the monolith).
MAX_CHOICES = 200
MAX_CHOICE_LENGTH = 100

Choice = Annotated[str, StringConstraints(min_length=1, max_length=MAX_CHOICE_LENGTH)]


# The request's data part: what the model may choose from, and the date it reads the receipt on. Unknown fields
# are refused, so a client can't believe it sent something the agent ignores.
class ReadingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The client's today (its injected clock), so "yesterday" printed on a receipt reads the same as in the app.
    today: date
    categories: list[Choice] = Field(max_length=MAX_CHOICES)
    payment_methods: list[Choice] = Field(max_length=MAX_CHOICES)


# One line of the receipt. Its docstring and descriptions are part of the schema the model reads.
class LineItem(BaseModel):
    """One line of the receipt: what was bought, and what that line cost."""

    description: str = Field(description="The item as printed, e.g. 'Paneer tikka x2'.")
    amount: DecimalText = Field(description='The line\'s price as a plain number string, e.g. "240.00", or null.')


# The answer, as the model fills it and as the artifact carries it. Its JSON schema is sent to the model, so the
# docstring and the field descriptions are instructions it reads. Every field is required, but most may be null:
# null is how the model says "the receipt doesn't show it", instead of inventing something.
class ReceiptExtraction(BaseModel):
    """What one shop receipt says. Use null for anything the receipt does not show; never guess."""

    merchant: str | None = Field(description="The shop or company name printed on the receipt, or null.")
    spent_on: date | None = Field(description="The purchase date printed on the receipt, or null.")
    line_items: list[LineItem] = Field(
        max_length=MAX_LINE_ITEMS, description="Each item bought, in the receipt's order; empty if none are listed."
    )
    tax: DecimalText = Field(description="The total tax (GST, VAT...) as a plain number string, or null.")
    total: DecimalText = Field(
        description='The final amount paid, as a plain number string without symbols or commas, e.g. "1250.50".'
    )
    currency: str | None = Field(
        description="The ISO 4217 code of the amounts, from the symbol or text on the receipt (₹ or Rs is INR)."
    )
    # The allowed payment methods are added to the schema per request (the client's list).
    payment_method: str | None = Field(
        description="Only if the receipt says how it was paid (a card, UPI, cash...); otherwise null."
    )
    # The allowed category names are added to the schema per request (the client's list).
    category: str | None = Field(description="The best matching category from the allowed list, or null.")


# The fields whose allowed values come with each request.
CATEGORY_FIELD = "category"
PAYMENT_METHOD_FIELD = "payment_method"
assert {CATEGORY_FIELD, PAYMENT_METHOD_FIELD} <= set(ReceiptExtraction.model_fields)
