"""The table access the approval commands share: forgetting expired cards, and storing one card.

The approvals' write side (like a domain module's repository), private to approvals/: forget_expired is used by
take_approval and store_card; store_card by request_approval and restore_approval (commands/). Like every
handler's work, it only stages changes in the bus's session; the bus commits.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlmodel import col, select

from app.core.cqrs import Context
from app.modules.assistant.approvals.models import MAX_PENDING, TTL_MINUTES, ExpenseSnapshot
from app.modules.assistant.approvals.persistence.tables import PendingApproval


def forget_expired(ctx: Context) -> None:
    """Delete every card shown more than TTL_MINUTES ago, in any thread. Run before each read or write."""
    cutoff = ctx.clock.now() - timedelta(minutes=TTL_MINUTES)
    ctx.session.execute(delete(PendingApproval).where(col(PendingApproval.created_at) < cutoff))


def store_card(
    ctx: Context, thread_id: str, approval_id: str, expense: ExpenseSnapshot, created_at: datetime
) -> None:
    """Save one card's record, dated `created_at`, then trim the table to the newest MAX_PENDING cards."""
    forget_expired(ctx)
    # merge: insert, or replace the same card's record.
    ctx.session.merge(
        PendingApproval(
            approval_id=approval_id, thread_id=thread_id, expense=expense.model_dump(mode="json"), created_at=created_at
        )
    )
    # Write the new row now, so the trim below counts it.
    ctx.session.flush()
    # Keep at most MAX_PENDING: forget the oldest beyond that.
    keep = select(PendingApproval.approval_id).order_by(col(PendingApproval.created_at).desc()).limit(MAX_PENDING)
    ctx.session.execute(delete(PendingApproval).where(col(PendingApproval.approval_id).not_in(keep)))
