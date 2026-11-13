"""The only code that reads or writes the chat message table."""

from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.modules.assistant.models import ChatMessage


def add_turn(session: Session, thread_id: str, turn: int, steps: list[dict[str, Any]]) -> None:
    # One commit for the whole turn, so a thread never holds half a turn.
    session.add_all(
        [ChatMessage(thread_id=thread_id, turn=turn, kind=step["type"], content=step) for step in steps]
    )
    session.commit()


def last_turn(session: Session, thread_id: str) -> int | None:
    """The newest turn number in a thread, or None if the thread doesn't exist."""
    return session.exec(select(func.max(ChatMessage.turn)).where(ChatMessage.thread_id == thread_id)).one()


def messages(session: Session, thread_id: str, from_turn: int = 1) -> list[ChatMessage]:
    """A thread's steps from `from_turn` onwards, oldest first."""
    statement = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id, ChatMessage.turn >= from_turn)
        .order_by(col(ChatMessage.id))
    )
    return list(session.exec(statement))
