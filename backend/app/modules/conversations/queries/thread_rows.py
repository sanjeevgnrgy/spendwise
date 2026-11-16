"""Reading a thread's stored rows, shared by the GetHistory and GetThread slices (get_history.py, get_thread.py).

Part of the conversations module's read side; it changes nothing. Only this module's query handlers use it: it
hands back table rows, which never leave the module (the handlers turn them into messages or readable copies).
"""

from sqlmodel import col, select

from app.core.cqrs import Context
from app.modules.conversations.persistence.tables import ConversationMessage


def thread_rows(ctx: Context, owner_id: int, thread_id: str, from_turn: int = 1) -> list[ConversationMessage]:
    """The owner's thread's rows from turn `from_turn` on, in the order they were stored (id order).

    Another person's thread with the same id is never read: a thread is its owner and its id together (D190).
    """
    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.owner_id == owner_id,
            ConversationMessage.thread_id == thread_id,
            ConversationMessage.turn >= from_turn,
        )
        .order_by(col(ConversationMessage.id))
    )
    return list(ctx.session.exec(statement))
