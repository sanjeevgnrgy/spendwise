"""GetLastTurn: the newest turn number in a thread, or None. The query and its handler; it changes nothing.

A slice of the conversations module's read side. module.py registers the handler with the bus. The assistant asks
it to number the next turn, and POST /chat to tell a thread it made from a typo.
"""

from sqlalchemy import func
from sqlmodel import select

from app.core.cqrs import Context, Query
from app.modules.conversations.persistence.tables import ConversationMessage
from app.modules.conversations.values import ThreadId


# The assistant numbers the next turn with it, and POST /chat uses None to refuse a thread id it never
# made (a typo should be an error, not a new conversation).
class GetLastTurn(Query[int | None]):
    """The newest turn number in a thread, or None if the thread doesn't exist yet."""

    thread_id: ThreadId


def get_last_turn(ctx: Context, query: GetLastTurn) -> int | None:
    """The highest turn number stored for the thread, or None if the thread has no messages (unknown)."""
    # MAX() in the database: one number comes back, not the thread's rows.
    statement = select(func.max(ConversationMessage.turn)).where(ConversationMessage.thread_id == query.thread_id)
    return ctx.session.exec(statement).one()
