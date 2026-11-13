"""Query handlers: read conversations. They never change anything."""

import json

from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context
from app.core.errors import NotFoundError
from app.core.llm import AssistantText, Message, Reasoning, ToolCall, ToolResult, UserText, messages_adapter
from app.modules.conversations.contracts import GetHistory, GetLastTurn, GetThread, ThreadMessage, ThreadRead
from app.modules.conversations.tables import ConversationMessage


def last_turn(ctx: Context, query: GetLastTurn) -> int | None:
    statement = select(func.max(ConversationMessage.turn)).where(ConversationMessage.thread_id == query.thread_id)
    return ctx.session.exec(statement).one()


def _rows(ctx: Context, thread_id: str, from_turn: int = 1) -> list[ConversationMessage]:
    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.thread_id == thread_id, ConversationMessage.turn >= from_turn)
        .order_by(col(ConversationMessage.id))
    )
    return list(ctx.session.exec(statement))


def history(ctx: Context, query: GetHistory) -> list[Message]:
    return messages_adapter.validate_python([row.content for row in _rows(ctx, query.thread_id, query.from_turn)])


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


def thread(ctx: Context, query: GetThread) -> ThreadRead:
    rows = _rows(ctx, query.thread_id)
    if not rows:
        raise NotFoundError(f"Thread {query.thread_id} not found")
    shown = []
    for row, message in zip(rows, messages_adapter.validate_python([row.content for row in rows]), strict=True):
        text = _readable(message)
        if text is not None:
            shown.append(ThreadMessage(turn=row.turn, kind=message.kind, text=text, created_at=row.created_at))
    return ThreadRead(thread_id=query.thread_id, messages=shown)
