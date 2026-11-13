"""Request and response bodies of the assistant's routes."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema

from app.modules.conversations import ThreadId
from app.modules.expenses import PaymentMethod
from app.modules.assistant.events import ToolCallSummary

# What one chat message may hold (also the web app's text box limit, via the generated contracts).
MAX_MESSAGE_LENGTH = 2000
MAX_NOTE_TEXT_LENGTH = 500


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_NOTE_TEXT_LENGTH, examples=["Paid 450.50 at Swiggy yesterday via GPay"])


# ParsedExpense's JSON schema is sent to the model as the shape its answer must have, so the docstring
# and field descriptions below are instructions it reads. Every field is required, but most may be
# null: the model must answer every field, and null is how it says "the text doesn't say".
# Without null, it would have to invent something.
class ParsedExpense(BaseModel):
    """One expense read from a short note the user wrote. Use null for anything the note does not say."""

    # The model's schema has no decimal type. A string keeps the exact digits (a JSON number could be
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
    payment_method: PaymentMethod | None = Field(
        description="Only if the text says how it was paid (GPay, PhonePe and Paytm UPI are upi); otherwise null."
    )
    note: str | None = Field(description="A few words on what was bought, or null.")


class ParseResponse(BaseModel):
    expense: ParsedExpense
    # Fields POST /expenses needs that the text didn't give. Empty means it's ready to save.
    missing_fields: list[str]


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1, max_length=MAX_MESSAGE_LENGTH, examples=["I spent 250 on lunch at Subway today, paid by UPI"]
    )
    # Leave it out to start a new conversation; send the thread_id from a reply to continue that one.
    thread_id: ThreadId | None = None


class ChatResponse(BaseModel):
    # Send this back with the next message to continue the same conversation.
    thread_id: str
    reply: str
    tool_calls: list[ToolCallSummary]
