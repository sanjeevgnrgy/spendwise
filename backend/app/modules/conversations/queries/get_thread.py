"""GetThread: a whole conversation as text for people. The query, its handler and the shapes it answers with.

A slice of the conversations module's read side; it never changes anything. module.py registers the handler with
the bus, and GET /threads/{id} (api.py) asks it. ThreadRead and ThreadMessage are REST responses, so their
docstrings are part of the OpenAPI document; notes for people reading the code are `#` comments.
"""

import json
from datetime import datetime

from pydantic import BaseModel

from app.core.cqrs import Context, Query
from app.core.errors import NotFoundError
from app.core.llm import (
    AssistantText,
    Message,
    MessageKind,
    Reasoning,
    ToolCall,
    ToolResult,
    UserText,
    messages_adapter,
)
from app.modules.conversations.queries.thread_rows import thread_rows
from app.modules.conversations.values import THREAD_NOT_FOUND, ThreadId


# One readable line of GET /threads/{id}: the message's text, or a tool call written as name(arguments).
# The model's private reasoning is left out (_readable, below).
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


# Asked by GET /threads/{id} (api.py).
class GetThread(Query[ThreadRead]):
    """The whole conversation, readable. Raises NotFoundError for an unknown thread."""

    thread_id: ThreadId


def _readable(message: Message) -> str | None:
    """A message as text for people, or None for the model's private reasoning (not shown)."""
    match message:
        case UserText(text=text) | AssistantText(text=text):
            return text
        case ToolCall(name=name, arguments=arguments):
            return f"{name}({json.dumps(arguments)})"
        case ToolResult(output=output):
            return output
        case Reasoning():
            return None


def get_thread(ctx: Context, query: GetThread) -> ThreadRead:
    """The whole thread, readable: each message as text, oldest first, without the model's reasoning.

    Raises NotFoundError if the thread has no messages (an unknown id).
    """
    rows = thread_rows(ctx, query.thread_id)
    if not rows:
        raise NotFoundError(THREAD_NOT_FOUND.format(thread_id=query.thread_id))
    shown = []
    for row, message in zip(rows, messages_adapter.validate_python([row.content for row in rows]), strict=True):
        text = _readable(message)
        if text is not None:
            shown.append(ThreadMessage(turn=row.turn, kind=message.kind, text=text, created_at=row.created_at))
    return ThreadRead(thread_id=query.thread_id, messages=shown)
