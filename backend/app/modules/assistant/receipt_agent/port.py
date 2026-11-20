"""The assistant's receipt-reading port: what the receipt turn needs from whoever reads receipts, and what it gets back.

Port. The receipt turn (application/receipt_turn.py) only knows ReceiptReader, ReadingRequest, ReceiptReading,
ReceiptExtraction and ReceiptAgentUnavailableError. The composition root (bootstrap.py) decides what's behind it,
through module.py: agent_reader.AgentReceiptReader, which sends the receipt to the receipt agent (agents/receipt)
through the remote-agents port (core/agents.py). A check passes a fake reader, or fake remote agents.

ReceiptExtraction is the assistant's own view of the agent's answer, and the adapter validates the answer against it:
to the assistant, a remote agent's output is outside data, never trusted as it comes (D199).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ExternalServiceError
from app.modules.expenses import PaymentMethod

# Bounds on what the agent may answer: a long supermarket bill fits, and nothing grows without limit. Generous on
# purpose: the form a person checks, and add_expense when they press Save, hold the expense's own limits.
MAX_LINE_ITEMS = 50
MAX_TEXT_LENGTH = 200
MAX_CURRENCY_LENGTH = 10
# The name the reading is shown under in the web panel: a tool call of its own, with its own chip (D200).
READ_RECEIPT = "read_receipt"


class ReceiptAgentUnavailableError(ExternalServiceError):
    """The receipt agent couldn't be used: not configured, unreachable, refused us, or not the agent we expect."""


@dataclass(frozen=True)
class ReadingRequest:
    """What the reader is given besides the file: the date to read it on, and the values it may choose from."""

    today: date
    categories: list[str]
    payment_methods: list[str]


# One line of a receipt, as the assistant accepts it.
class LineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    description: str = Field(max_length=MAX_TEXT_LENGTH)
    amount: Decimal | None


# What a receipt says, as the assistant accepts it from the agent. Fields it doesn't know are ignored (a newer
# agent may add some); a known field of the wrong type or size makes the whole answer unusable.
class ReceiptExtraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    merchant: str | None = Field(max_length=MAX_TEXT_LENGTH)
    spent_on: date | None
    line_items: list[LineItem] = Field(max_length=MAX_LINE_ITEMS)
    tax: Decimal | None
    total: Decimal | None
    currency: str | None = Field(max_length=MAX_CURRENCY_LENGTH)
    payment_method: PaymentMethod | None
    category: str | None = Field(max_length=MAX_TEXT_LENGTH)


@dataclass(frozen=True)
class ReceiptReading:
    """How one reading went: the reader's id for it (the A2A task id, if it got that far and it's a safe value to
    show) and what the receipt says, or None if it couldn't be read (the agent failed, refused, or answered
    something unusable)."""

    task_id: str | None
    extraction: ReceiptExtraction | None


class ReceiptReader(Protocol):
    """Reads a receipt's file into a ReceiptExtraction. Saves nothing: the answer is a suggestion to confirm."""

    def read(self, data: bytes, media_type: str, request: ReadingRequest) -> ReceiptReading:
        """Read one receipt (`media_type` is one of the receipts module's). A reading that ran but failed comes back
        with extraction=None, not raised. Raises ReceiptAgentUnavailableError if no reading could be asked for."""
        ...
