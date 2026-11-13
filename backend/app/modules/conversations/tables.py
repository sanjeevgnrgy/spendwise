from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlmodel import Field, SQLModel

from app.modules.conversations.contracts import THREAD_ID_MAX_LENGTH

KIND_LENGTH = 30


class ConversationMessage(SQLModel, table=True):
    """One message of a chat thread. Private to this module: other modules never import it."""

    __tablename__ = "conversation_message"

    id: int | None = Field(default=None, primary_key=True)
    # Groups one conversation.
    thread_id: str = Field(index=True, max_length=THREAD_ID_MAX_LENGTH)
    # 1 for the first user message in a thread, 2 for the next, ... Lets us keep only the last N turns.
    turn: int
    # The message's kind (user_text, tool_call, ...), also inside `content`: a column so it can be filtered.
    kind: str = Field(max_length=KIND_LENGTH)
    # The provider-neutral message (core/llm/messages.py) as JSON. Not any provider's own format.
    content: dict[str, Any] = Field(sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))


TABLES = (ConversationMessage,)
