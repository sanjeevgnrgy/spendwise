"""What the approval commands share: the card's snapshot of an expense, a taken card, its id, and the limits.

The approvals' shared models (like a domain module's models.py and values.py). The command slices (commands/)
and store.py use it; persistence/tables.py takes APPROVAL_ID_LENGTH from it; the package's __init__.py re-exports
it for the rest of the assistant (application/assistant.py and application/decisions.py).
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.modules.mcp import ExpenseView

# An unanswered card stops working after this long, and at most this many are remembered. A short life
# means an old card, scrolled out of sight, can't delete anything; the cap keeps the table small even if
# cards are never answered. (application/decisions.py quotes TTL_MINUTES to the user: ChatText.STALE_APPROVAL.)
TTL_MINUTES = 15
MAX_PENDING = 200

# The longest card id stored (ApprovalId below checks the same limit in the commands, and the table's column
# has it too). The ids the assistant makes ("approval_" + 32 hex characters, application/assistant.py) fit
# with room to spare.
APPROVAL_ID_LENGTH = 64

# The card's surface id (what the browser sends back with a click).
ApprovalId = Annotated[str, Field(min_length=1, max_length=APPROVAL_ID_LENGTH)]


class ExpenseSnapshot(BaseModel):
    """The expense exactly as a card showed it, in the assistant's own terms.

    A copy, not the MCP contract's ExpenseView: rows stored here must keep reading correctly even if
    that contract changes later.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: int
    version: int  # Approve deletes only this version (DeleteExpense.expected_version)
    amount: str
    currency: str
    category: str
    merchant: str
    note: str | None
    spent_on: str
    payment_method: str

    @classmethod
    def of(cls, expense: ExpenseView) -> ExpenseSnapshot:
        """The snapshot of an expense the tools returned.

        Made from its JSON form (amount, date and payment method as text), the same form the table
        stores, so a fresh snapshot and a stored one compare equal when nothing has changed.
        """
        return cls.model_validate(expense.model_dump(mode="json"))


# What TakeApproval returns: the card's snapshot, plus when it was shown, so RestoreApproval can put
# it back with its original age.
class PendingCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    expense: ExpenseSnapshot
    created_at: datetime
