"""GetHistory: a thread's messages from a given turn on, the history resent to the model. The query and its handler.

A slice of the conversations module's read side; it never changes anything. module.py registers the handler with
the bus; the assistant asks it before each run and gets provider-neutral messages, never table rows.
"""

from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.core.llm import Message, messages_adapter
from app.modules.conversations.queries.thread_rows import thread_rows
from app.modules.conversations.values import ThreadId


# The assistant asks only for its last few turns (from_turn), so old messages stop costing tokens; whole
# turns, so a tool call is never cut off from its result. A from_turn of 0 or less means "from the start".
class GetHistory(Query[list[Message]]):
    """The owner's thread's messages from `from_turn` onwards, oldest first: the history resent to the model."""

    owner_id: UserId
    thread_id: ThreadId
    from_turn: int = 1


def get_history(ctx: Context, query: GetHistory) -> list[Message]:
    """The thread's messages from `from_turn` on, oldest first, as neutral messages for the model.

    An unknown thread (or another person's, which is the same to this owner) gives an empty list: a new conversation
    simply has no history yet.
    """
    rows = thread_rows(ctx, query.owner_id, query.thread_id, query.from_turn)
    return messages_adapter.validate_python([row.content for row in rows])
