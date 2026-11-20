"""RememberTask: keep a remote agent's waiting task for this conversation, so the person's next message answers it.

A vertical slice of the delegation: the command and its handler. The delegator (delegation/delegator.py) sends it when
an agent's task stops INPUT_REQUIRED; module.py registers remember_task on the bus.
"""

from sqlalchemy import delete
from sqlmodel import col, select

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.assistant.delegation.models import MAX_PENDING, PendingTask
from app.modules.assistant.delegation.persistence.tables import PendingDelegation
from app.modules.conversations import ThreadId


# Sent by the delegator when an agent asks the person something. One per conversation: a newer one replaces it.
class RememberTask(Command[None]):
    """Keep `task` as the one waiting in `owner_id`'s conversation `thread_id`."""

    owner_id: UserId
    thread_id: ThreadId
    task: PendingTask


def remember_task(ctx: Context, command: RememberTask) -> None:
    """Handler for RememberTask: replace the conversation's waiting task, then keep at most MAX_PENDING per person."""
    # merge: insert, or replace the conversation's earlier waiting task (the key is the owner and the conversation).
    ctx.session.merge(
        PendingDelegation(
            owner_id=command.owner_id,
            thread_id=command.thread_id,
            created_at=ctx.clock.now(),
            **command.task.model_dump(),
        )
    )
    ctx.session.flush()
    # Beyond the cap, the person's oldest waiting tasks are forgotten (an unanswered question, nothing more). Per
    # person, so one person's can never push out another's (D190).
    theirs = col(PendingDelegation.owner_id) == command.owner_id
    keep = (
        select(PendingDelegation.thread_id)
        .where(theirs)
        .order_by(col(PendingDelegation.created_at).desc())
        .limit(MAX_PENDING)
    )
    ctx.session.execute(delete(PendingDelegation).where(theirs, col(PendingDelegation.thread_id).not_in(keep)))
