"""RequestApproval: remember a delete card as it's shown, so its Approve can later delete exactly that expense.

A vertical slice of the approvals: the command and its handler. The Assistant use case (application/assistant.py)
sends it while the agent shows a delete card; module.py registers request_approval on the bus.
"""

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.assistant.approvals.models import ApprovalId, ExpenseSnapshot
from app.modules.assistant.approvals.store import store_card
from app.modules.conversations import ThreadId


# Sent by the Assistant use case (application/assistant.py) while the agent shows a delete card; `approval_id`
# becomes the card's surface id.
class RequestApproval(Command[None]):
    """Remember that this card's Approve may delete this expense, as shown (for its owner, in this conversation
    only)."""

    owner_id: UserId
    thread_id: ThreadId
    approval_id: ApprovalId
    expense: ExpenseSnapshot


def request_approval(ctx: Context, command: RequestApproval) -> None:
    """Handler for RequestApproval: remember a card that's being shown now."""
    store_card(ctx, command.owner_id, command.thread_id, command.approval_id, command.expense, ctx.clock.now())
