"""TakeTask: read this conversation's waiting task and forget it in one step, so each answer resumes it once.

A vertical slice of the delegation: the command and its handler. The delegator (delegation/delegator.py) sends it at
the start of every turn; module.py registers take_task on the bus.
"""

from datetime import timedelta

from sqlalchemy import delete
from sqlmodel import col, select

from app.core.cqrs import Command, Context
from app.core.ids import UserId
from app.modules.assistant.delegation.models import TTL_MINUTES, PendingTask
from app.modules.assistant.delegation.persistence.tables import PendingDelegation
from app.modules.conversations import ThreadId


# Sent by the delegator before each turn in a conversation.
class TakeTask(Command[PendingTask | None]):
    """The conversation's waiting task, forgotten as it's returned; None if there's none (or it's too old).

    Like TakeApproval, a deliberate exception to "commands return at most an id": reading and removing must be one
    step, or two messages could both resume the task.
    """

    owner_id: UserId
    thread_id: ThreadId


def take_task(ctx: Context, command: TakeTask) -> PendingTask | None:
    """Handler for TakeTask: forget tasks older than TTL_MINUTES, then return and delete this conversation's."""
    cutoff = ctx.clock.now() - timedelta(minutes=TTL_MINUTES)
    ctx.session.execute(delete(PendingDelegation).where(col(PendingDelegation.created_at) < cutoff))
    # The owner in the same statement as the conversation: another person's waiting task is never found (D190).
    pending = ctx.session.exec(
        select(PendingDelegation).where(
            col(PendingDelegation.owner_id) == command.owner_id, col(PendingDelegation.thread_id) == command.thread_id
        )
    ).first()
    if pending is None:
        return None
    ctx.session.delete(pending)
    return PendingTask(agent=pending.agent, skill=pending.skill, task_id=pending.task_id, context_id=pending.context_id)
