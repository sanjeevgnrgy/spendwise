from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema

from app.modules import expenses


class AskRequest(BaseModel):
    # The upper limit matters because every character is sent to Gemini and paid for as tokens.
    prompt: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500, examples=["Paid 450.50 at Swiggy yesterday via GPay"])


# ParsedExpense's JSON schema is sent to Gemini as the shape its answer must have, so the docstring
# and field descriptions below are instructions Gemini reads. Every field is required, but most may
# be null: Gemini must answer every field, and null is how it says "the text doesn't say".
# Without null, it would have to invent something.
class ParsedExpense(BaseModel):
    """One expense read from a short note the user wrote. Use null for anything the note does not say."""

    # Gemini's schema has no decimal type. A string keeps the exact digits (a JSON number could be
    # read as a float); Pydantic then turns it into a Decimal, which the API returns as "450.50".
    amount: Annotated[Decimal | None, WithJsonSchema({"type": ["string", "null"]})] = Field(
        description='The amount as a plain number string, e.g. "1250.50", with no currency symbol or commas. '
        "null if the text does not state an amount. Never guess an amount."
    )
    currency: str = Field(description="ISO 4217 code such as INR, USD or EUR. INR unless another currency is clearly stated.")
    # The allowed category names are added to the schema per request (see parse.py).
    category: str | None = Field(description="The best matching category from the allowed list, or null if none fits.")
    merchant: str | None = Field(description="The shop, company or person paid, or null if not mentioned.")
    spent_on: date = Field(
        description="The date of the expense. Work out words like 'yesterday' or 'last Friday' from today's date; "
        "use today if no date is mentioned."
    )
    payment_method: expenses.PaymentMethod | None = Field(
        description="Only if the text says how it was paid (GPay, PhonePe and Paytm UPI are upi); otherwise null."
    )
    note: str | None = Field(description="A few words on what was bought, or null.")


class ParseResponse(BaseModel):
    expense: ParsedExpense
    # Fields POST /expenses needs that the text didn't give. Empty means it's ready to save.
    missing_fields: list[str]
