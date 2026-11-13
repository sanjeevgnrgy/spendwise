"""The conversations module's contract: stored chat threads, in provider-neutral messages.

A thread is a list of turns. A turn is one user message and everything up to the reply (tool calls,
their results, the model's reasoning), stored together so a history never holds half a turn.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.core.cqrs import Command, Query
from app.core.llm import Message, MessageKind

THREAD_ID_MAX_LENGTH = 32
# The browser names AG-UI threads; the server names /chat ones (a 32-character hex id).
ThreadId = Annotated[str, Field(min_length=1, max_length=THREAD_ID_MAX_LENGTH)]


class ThreadMessage(BaseModel):
    """One message of a conversation, made readable."""

    turn: int
    kind: MessageKind
    text: str
    created_at: datetime


class ThreadRead(BaseModel):
    thread_id: str
    messages: list[ThreadMessage]


# ---------- commands ----------


class AppendTurn(Command[None]):
    """Store one whole turn (it's saved only once the run has succeeded)."""

    thread_id: ThreadId
    turn: int = Field(ge=1)
    messages: list[Message]


# ---------- queries ----------


class GetLastTurn(Query[int | None]):
    """The newest turn number in a thread, or None if the thread doesn't exist yet."""

    thread_id: ThreadId


class GetHistory(Query[list[Message]]):
    """A thread's messages from `from_turn` onwards, oldest first: the history resent to the model."""

    thread_id: ThreadId
    from_turn: int = 1


class GetThread(Query[ThreadRead]):
    """The whole conversation, readable. Raises NotFoundError for an unknown thread."""

    thread_id: ThreadId
