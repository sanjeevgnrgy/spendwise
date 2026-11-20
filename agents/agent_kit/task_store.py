"""Every agent's task store: the SDK's in-memory store, keeping a few recent tasks and never a file's bytes.

Part of the agent kit, given to each agent's request handler by server.build_agent_app. The SDK's InMemoryTaskStore
keeps every task until the process stops, with its history, and the history holds the request: for the receipt agent,
a receipt's bytes, up to 5 MB each. This store (D198) replaces each file part's bytes with a short note before a
task is kept, and keeps only the MAX_KEPT_TASKS most recent tasks, so the agent holds no receipt once it has
answered and its memory stays bounded. A client still gets each task's states and artifact as they happen.

A task waiting for the client (INPUT_REQUIRED: the insights agent asking which month) must still be there when the
answer comes, so when the store is full it forgets finished tasks first, oldest first, and a waiting one only if
every kept task is waiting (D205).
"""

import asyncio
from collections import OrderedDict

from a2a.server.context import ServerCallContext
from a2a.server.tasks import InMemoryTaskStore, TaskStore
from a2a.types import ListTasksRequest, ListTasksResponse, Task, TaskState

# Enough for a few clients' tasks still being read or just answered; older ones are forgotten.
MAX_KEPT_TASKS = 20
# What a file part says once its bytes are dropped (protocol text, for whoever lists the task).
FILE_NOT_KEPT = "(file not kept)"
# The states in which a task waits for its client, and is forgotten last.
WAITING_STATES = frozenset({TaskState.TASK_STATE_INPUT_REQUIRED, TaskState.TASK_STATE_AUTH_REQUIRED})


class ForgetfulTaskStore(TaskStore):
    """A TaskStore that keeps at most `limit` tasks, each without its files' bytes, forgetting the oldest finished
    task first (a waiting one last)."""

    def __init__(self, inner: TaskStore | None = None, limit: int = MAX_KEPT_TASKS) -> None:
        """Wrap `inner` (a new InMemoryTaskStore by default) and keep at most `limit` tasks in it."""
        self._inner = inner or InMemoryTaskStore()
        self._limit = limit
        # Task ids, least recently saved first, each with the context it was saved under (the store is per owner) and
        # whether it's waiting for its client.
        self._kept: OrderedDict[str, tuple[ServerCallContext, bool]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def save(self, task: Task, context: ServerCallContext) -> None:
        """Keep `task` without its files' bytes, then forget tasks beyond the limit: the oldest that isn't waiting."""
        async with self._lock:
            await self._inner.save(_without_files(task), context)
            self._kept[task.id] = (context, task.status.state in WAITING_STATES)
            self._kept.move_to_end(task.id)
            while len(self._kept) > self._limit:
                old_id = next((kept for kept, (_, waiting) in self._kept.items() if not waiting), None)
                old_id = old_id if old_id is not None else next(iter(self._kept))
                old_context, _ = self._kept.pop(old_id)
                await self._inner.delete(old_id, old_context)

    async def get(self, task_id: str, context: ServerCallContext) -> Task | None:
        """The kept task with this id, or None (never kept, or already forgotten)."""
        return await self._inner.get(task_id, context)

    async def list(self, params: ListTasksRequest, context: ServerCallContext) -> ListTasksResponse:
        """The kept tasks matching `params`, as the inner store lists them."""
        return await self._inner.list(params, context)

    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        """Forget the task with this id."""
        async with self._lock:
            self._kept.pop(task_id, None)
            await self._inner.delete(task_id, context)


def _without_files(task: Task) -> Task:
    """A copy of `task` whose history's file parts hold a short note instead of their bytes."""
    kept = Task()
    kept.CopyFrom(task)
    for message in kept.history:
        for part in message.parts:
            if part.HasField("raw"):
                part.text = FILE_NOT_KEPT  # setting the text clears the bytes: a part holds one kind of content
    return kept
