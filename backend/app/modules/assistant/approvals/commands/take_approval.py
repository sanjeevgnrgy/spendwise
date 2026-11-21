"""TakeApproval: read a delete card's record and forget it in one step, so each card decides once.

A vertical slice of the approvals: the command and its handler. The Assistant use case (application/assistant.py)
sends it when Approve or Cancel arrives; module.py registers take_approval on the bus.
"""

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.assistant.approvals.models import ApprovalId, ExpenseSnapshot, PendingCard
from app.modules.assistant.approvals.persistence.tables import PendingApproval
from app.modules.assistant.approvals.store import forget_expired
from app.modules.conversations import ThreadId


# Sent by Assistant.decide (application/assistant.py) when Approve or Cancel arrives, with the thread and the
# card's surface id.
class TakeApproval(Command[PendingCard | None]):
    """The card's record, forgotten as it's returned: each card decides once.

    None if it was already answered, has expired, or belongs to another conversation or another person.

    A deliberate exception to "commands return at most an id": reading and removing the record must be
    one step (like taking a message off a queue), or two clicks could both get it.
    """

    owner_id: UserId
    thread_id: ThreadId
    approval_id: ApprovalId


def take_approval(ctx: Context, command: TakeApproval) -> PendingCard | None:
    """Handler for TakeApproval: return the card's record and delete it, in the same transaction.

    None if the owner has no live card by that id in this thread: already answered, expired, never shown, another
    conversation's or another person's. The bus commits the delete as this returns, so the card can't decide twice.
    """
    # Expired cards go first, so a card past its TTL_MINUTES is simply not found.
    forget_expired(ctx)
    pending = ctx.session.get(PendingApproval, command.approval_id)
    # Another person's card, or another conversation's, is treated as unknown, and left alone (D190).
    if pending is None or pending.owner_id != command.owner_id or pending.thread_id != command.thread_id:
        return None
    ctx.session.delete(pending)
    return PendingCard(expense=ExpenseSnapshot.model_validate(pending.expense), created_at=pending.created_at)
