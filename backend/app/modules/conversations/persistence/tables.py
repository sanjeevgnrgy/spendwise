"""The conversations module's table: `conversation_message`, one row per message of a chat thread.

Private to this module: only its handlers read or write it (commands/append_turn.py appends a finished turn, the
query slices in queries/ read a thread back, whole or from a given turn). Other modules use the contract (the
package's __init__.py), and the composition root hands TABLES to the migrations. The table itself is created and
changed by Alembic migrations, never by the app.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index
from sqlmodel import Field, SQLModel

from app.modules.conversations.values import THREAD_ID_MAX_LENGTH

# The longest message kind that fits; the longest today, "assistant_text", is 14 characters.
KIND_LENGTH = 30
# Every read picks one person's thread and a range of its turns (the history from a given turn, the highest turn so
# far), so this index finds those rows directly instead of walking the whole thread. Migration 0007 adds it (it
# replaces 0004's index on the thread and turn alone).
OWNER_THREAD_TURN_INDEX = "ix_conversation_message_owner_id_thread_id_turn"


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class ConversationMessage(SQLModel, table=True):
    """One message of a chat thread. Private to this module: other modules never import it."""

    __tablename__ = "conversation_message"  # pyright: ignore[reportAssignmentType]  (SQLModel declares it as declared_attr)
    __table_args__ = (Index(OWNER_THREAD_TURN_INDEX, "owner_id", "thread_id", "turn"),)

    # None until the row is inserted; the database assigns it. Also the order of a thread's messages.
    id: int | None = Field(default=None, primary_key=True)
    # Whose conversation it is (core.ids.UserId; no foreign key: the users table is the accounts module's). A thread
    # is its owner and its id together: the browser names threads, so two people may pick the same id, and each gets
    # their own conversation (D190). Indexed through OWNER_THREAD_TURN_INDEX, which starts with it.
    owner_id: int
    # Groups one conversation (of its owner's).
    thread_id: str = Field(max_length=THREAD_ID_MAX_LENGTH)
    # 1 for the first user message in a thread, 2 for the next, ... Lets us keep only the last N turns.
    turn: int
    # The message's kind (user_text, tool_call, ...), also inside `content`: a column so it can be filtered.
    kind: str = Field(max_length=KIND_LENGTH)
    # The provider-neutral message (core/llm/messages.py) as JSON. Not any provider's own format.
    content: dict[str, Any] = Field(sa_type=JSON)
    # UTC, always from the app's injected clock (append_turn). No default on purpose: a row made without it
    # fails at the INSERT (the column is NOT NULL) instead of quietly getting the server's own time.
    created_at: datetime = Field(sa_type=DateTime(timezone=True))


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (ConversationMessage,)
