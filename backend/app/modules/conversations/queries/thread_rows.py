"""Reading a thread's stored rows, shared by the GetHistory and GetThread slices (get_history.py, get_thread.py).

Part of the conversations module's read side; it changes nothing. Only this module's query handlers use it: it
hands back table rows, which never leave the module (the handlers turn them into messages or readable copies).
"""

from sqlmodel import col, select

from app.core.cqrs import Context
from app.modules.conversations.persistence.tables import ConversationMessage


def thread_rows(ctx: Context, thread_id: str, from_turn: int = 1) -> list[ConversationMessage]:
    """The thread's rows from turn `from_turn` on, in the order they were stored (id order)."""
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.thread_id == thread_id, ConversationMessage.turn >= from_turn)
        .order_by(col(ConversationMessage.id))
    )
    return list(ctx.session.exec(statement))
