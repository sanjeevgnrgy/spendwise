"""Human in the loop: deletes the assistant may only carry out after the user approves them.

In the web panel the model can't delete at all: whatever it asks, the expense is only looked up and
shown with Approve and Cancel (agent.py). The real delete happens when the user presses Approve,
and the server decides WHAT gets deleted from its own record of that card (a snapshot of the
expense), never from what the browser sends.
"""

from datetime import datetime, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete
from sqlmodel import col, select

from app.core.cqrs import Command, Context
from app.modules.assistant.tables import APPROVAL_ID_LENGTH, PendingApproval
from app.modules.conversations import ThreadId
from app.modules.mcp import ExpenseView

# An unanswered card stops working after this long, and at most this many are remembered.
TTL_MINUTES = 15
MAX_PENDING = 200

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
    def of(cls, expense: ExpenseView) -> "ExpenseSnapshot":
        return cls.model_validate(expense.model_dump(mode="json"))


class PendingCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    expense: ExpenseSnapshot
    created_at: datetime


class RequestApproval(Command[None]):
    """Remember that this card's Approve may delete this expense, as shown (in this conversation only)."""

    thread_id: ThreadId
    approval_id: ApprovalId
    expense: ExpenseSnapshot


class TakeApproval(Command[PendingCard | None]):
    """The card's record, forgotten as it's returned: each card decides once.

    None if it was already answered, has expired, or belongs to another conversation.

    A deliberate exception to "commands return at most an id": reading and removing the record must be
    one step (like taking a message off a queue), or two clicks could both get it.
    """

    thread_id: ThreadId
    approval_id: ApprovalId


class RestoreApproval(Command[None]):
    """Put a taken card back, unchanged (same snapshot, same age), after the decision failed midway."""

    thread_id: ThreadId
    approval_id: ApprovalId
    card: PendingCard


def _forget_expired(ctx: Context) -> None:
    cutoff = ctx.clock.now() - timedelta(minutes=TTL_MINUTES)
    ctx.session.execute(delete(PendingApproval).where(col(PendingApproval.created_at) < cutoff))


def _store(ctx: Context, thread_id: str, approval_id: str, expense: ExpenseSnapshot, created_at: datetime) -> None:
    _forget_expired(ctx)
    # merge: insert, or replace the same card's record.
    ctx.session.merge(
        PendingApproval(
            approval_id=approval_id, thread_id=thread_id, expense=expense.model_dump(mode="json"), created_at=created_at
        )
    )
    ctx.session.flush()
    # Keep at most MAX_PENDING: forget the oldest beyond that.
    keep = select(PendingApproval.approval_id).order_by(col(PendingApproval.created_at).desc()).limit(MAX_PENDING)
    ctx.session.execute(delete(PendingApproval).where(col(PendingApproval.approval_id).not_in(keep)))


def request_approval(ctx: Context, command: RequestApproval) -> None:
    _store(ctx, command.thread_id, command.approval_id, command.expense, ctx.clock.now())


def restore_approval(ctx: Context, command: RestoreApproval) -> None:
    # The original time, so a card that keeps failing still expires TTL_MINUTES after it was shown.
    _store(ctx, command.thread_id, command.approval_id, command.card.expense, command.card.created_at)


def take_approval(ctx: Context, command: TakeApproval) -> PendingCard | None:
    _forget_expired(ctx)
    pending = ctx.session.get(PendingApproval, command.approval_id)
    # Another conversation's card is treated as unknown, and left alone.
    if pending is None or pending.thread_id != command.thread_id:
        return None
    ctx.session.delete(pending)
    return PendingCard(expense=ExpenseSnapshot.model_validate(pending.expense), created_at=pending.created_at)
