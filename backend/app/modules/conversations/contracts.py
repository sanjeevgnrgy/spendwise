"""The conversations module's contract: stored chat threads, in provider-neutral messages.

A thread is a list of turns. A turn is one user message and everything up to the reply (tool calls,
their results, the model's reasoning), stored together so a history never holds half a turn.

The conversations module's contract layer: everything here is exported from the package's __init__.py.
Used by the assistant (to store and resend turns) and by GET /threads/{id} (api.py). ThreadRead and
ThreadMessage are REST responses, so their docstrings are part of the OpenAPI document; notes for people
reading the code are `#` comments.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.core.cqrs import Command, Query
from app.core.llm import Message, MessageKind

# The longest thread id accepted: also the table column's length (tables.py).
THREAD_ID_MAX_LENGTH = 32
# The 404 text for a thread id with no messages; the assistant uses it too, for a /chat thread it can't continue.
THREAD_NOT_FOUND = "Thread {thread_id} not found"
# The browser names AG-UI threads; the server names /chat ones (a 32-character hex id).
ThreadId = Annotated[str, Field(min_length=1, max_length=THREAD_ID_MAX_LENGTH)]


# One readable line of GET /threads/{id}: the message's text, or a tool call written as name(arguments).
# The model's private reasoning is left out (queries._readable).
class ThreadMessage(BaseModel):
    """One message of a conversation, made readable."""

    turn: int
    kind: MessageKind
    text: str
    created_at: datetime


# GetThread's answer and the body of GET /threads/{id}: the thread's readable messages, oldest first.
class ThreadRead(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


# ---------- commands ----------


# Sent by the assistant once a run has finished. `turn` is the next number after GetLastTurn's (1 for a
# new thread); the messages are stored in the order given.
class AppendTurn(Command[None]):
    """Store one whole turn (it's saved only once the run has succeeded)."""

    thread_id: ThreadId
    turn: int = Field(ge=1)
    messages: list[Message]


# ---------- queries ----------


# The assistant numbers the next turn with it, and POST /chat uses None to refuse a thread id it never
# made (a typo should be an error, not a new conversation).
class GetLastTurn(Query[int | None]):
    """The newest turn number in a thread, or None if the thread doesn't exist yet."""

    thread_id: ThreadId


# The assistant asks only for its last few turns (from_turn), so old messages stop costing tokens; whole
# turns, so a tool call is never cut off from its result. A from_turn of 0 or less means "from the start".
class GetHistory(Query[list[Message]]):
    """A thread's messages from `from_turn` onwards, oldest first: the history resent to the model."""

    thread_id: ThreadId
    from_turn: int = 1


# Asked by GET /threads/{id} (api.py).
class GetThread(Query[ThreadRead]):
    """The whole conversation, readable. Raises NotFoundError for an unknown thread."""

    thread_id: ThreadId
