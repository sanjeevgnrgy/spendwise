"""Conversations module: stored chat threads, so a conversation can carry on across messages.

A thread is a list of turns. A turn is one user message and everything up to the reply (tool calls,
their results, the model's reasoning), stored together so a history never holds half a turn. Messages are
stored provider-neutral (core/llm/messages.py).

Public interface: other modules import ONLY the contract names below, from `app.modules.conversations`,
and send them through the bus. The table, handlers and router stay private; the composition root
(bootstrap.py) plugs them in through module.py.

Inside, each command and each query is one file holding the message and its handler (commands/, queries/).
The thread id's type, its limit and the "not found" text are in values.py, and the table is in persistence/.
This file only re-exports the contract names from those files.

Who uses it: the assistant (GetLastTurn numbers the next turn and tells a known thread from a typo,
GetHistory gives the model the recent turns, AppendTurn stores a finished turn) and GET /threads/{id}
(GetThread).
"""

from app.modules.conversations.commands.append_turn import AppendTurn
from app.modules.conversations.queries.get_history import GetHistory
from app.modules.conversations.queries.get_last_turn import GetLastTurn
from app.modules.conversations.queries.get_thread import GetThread, ThreadRead
from app.modules.conversations.values import THREAD_ID_MAX_LENGTH, THREAD_NOT_FOUND, ThreadId

__all__ = [
    "THREAD_ID_MAX_LENGTH",
    "THREAD_NOT_FOUND",
    "AppendTurn",
    "GetHistory",
    "GetLastTurn",
    "GetThread",
    "ThreadId",
    "ThreadRead",
]
