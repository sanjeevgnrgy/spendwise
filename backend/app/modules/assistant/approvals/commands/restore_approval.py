"""RestoreApproval: put a taken delete card back exactly as it was, after the decision failed midway.

A vertical slice of the approvals: the command and its handler. The Assistant use case (application/assistant.py)
sends it when something fails after TakeApproval; module.py registers restore_approval on the bus.
"""

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.assistant.approvals.models import ApprovalId, PendingCard
from app.modules.assistant.approvals.store import store_card
from app.modules.conversations import ThreadId


# Sent by Assistant.decide (application/assistant.py) when something fails after the card was taken.
class RestoreApproval(Command[None]):
    """Put a taken card back, unchanged (same owner, snapshot and age), after the decision failed midway."""

    owner_id: UserId
    thread_id: ThreadId
    approval_id: ApprovalId
    card: PendingCard


def restore_approval(ctx: Context, command: RestoreApproval) -> None:
    """Handler for RestoreApproval: put a taken card back, with its original snapshot and time."""
    # The original time, so a card that keeps failing still expires TTL_MINUTES after it was shown.
    card = command.card
    store_card(ctx, command.owner_id, command.thread_id, command.approval_id, card.expense, card.created_at)
