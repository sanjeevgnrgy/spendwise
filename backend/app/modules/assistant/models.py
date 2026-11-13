from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


class ChatMessage(SQLModel, table=True):
    """One step of a chat thread. Private to the assistant module: other modules never import it.

    Stored so that later messages in the same thread can include the conversation so far.
    """

    id: int | None = Field(default=None, primary_key=True)
    # Groups one conversation. The server picks it (a random UUID) when a thread starts.
    thread_id: str = Field(index=True, max_length=32)
    # 1 for the first user message in a thread, 2 for the next, ... Lets us keep only the last N turns.
    turn: int
    # Gemini's step type: user_input, thought, function_call, function_result or model_output.
    kind: str = Field(max_length=30)
    # The step exactly as sent to or received from Gemini, so it can be resent unchanged.
    content: dict[str, Any] = Field(sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
