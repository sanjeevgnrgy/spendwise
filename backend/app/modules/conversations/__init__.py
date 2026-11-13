"""Conversations module: stored chat threads, so a conversation can carry on across messages.

Public interface: other modules import ONLY the contract names below, from `app.modules.conversations`,
and send them through the bus. The table, handlers and router stay private.
"""

from app.modules.conversations.contracts import (
    THREAD_ID_MAX_LENGTH,
    AppendTurn,
    GetHistory,
    GetLastTurn,
    GetThread,
    ThreadId,
    ThreadRead,
)

__all__ = ["THREAD_ID_MAX_LENGTH", "AppendTurn", "GetHistory", "GetLastTurn", "GetThread", "ThreadId", "ThreadRead"]
