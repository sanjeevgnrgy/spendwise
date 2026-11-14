"""Conversations module: stored chat threads, so a conversation can carry on across messages.

Public interface: other modules import ONLY the contract names below, from `app.modules.conversations`,
and send them through the bus. The table, handlers and router stay private; the composition root
(bootstrap.py) plugs them in through module.py.

Who uses it: the assistant (GetLastTurn numbers the next turn and tells a known thread from a typo,
GetHistory gives the model the recent turns, AppendTurn stores a finished turn) and GET /threads/{id}
(GetThread).
"""

from app.modules.conversations.contracts import (
    THREAD_ID_MAX_LENGTH,
    THREAD_NOT_FOUND,
    AppendTurn,
    GetHistory,
    GetLastTurn,
    GetThread,
    ThreadId,
    ThreadRead,
)

__all__ = ["THREAD_ID_MAX_LENGTH", "THREAD_NOT_FOUND", "AppendTurn", "GetHistory", "GetLastTurn", "GetThread", "ThreadId", "ThreadRead"]
