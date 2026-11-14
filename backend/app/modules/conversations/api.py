"""HTTP routes for conversations: read a stored thread. They only translate HTTP into queries.

The conversations module's REST adapter. The composition root mounts `router` under /api/v1. Threads are
written only by the assistant (AppendTurn), so there is no route to change one.
"""

from typing import Annotated

from fastapi import APIRouter, Path

from app.modules.conversations.queries.get_thread import GetThread, ThreadRead
from app.modules.conversations.values import THREAD_ID_MAX_LENGTH
from app.web.dependencies import BusDep

router = APIRouter(tags=["conversations"])


# GET /api/v1/threads/{thread_id}: the whole conversation as text for people, oldest first; a 404 problem
# for an unknown thread. The path's length limit matches ThreadId, so a too-long id is a 422, not a
# lookup. (A route's docstring would become its OpenAPI text, so notes go here.)
@router.get("/threads/{thread_id}")
def get_thread(thread_id: Annotated[str, Path(max_length=THREAD_ID_MAX_LENGTH)], bus: BusDep) -> ThreadRead:
    return bus.ask(GetThread(thread_id=thread_id))
