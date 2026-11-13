"""HTTP routes for conversations: read a stored thread."""

from typing import Annotated

from fastapi import APIRouter, Path

from app.core.dependencies import BusDep
from app.modules.conversations.contracts import THREAD_ID_MAX_LENGTH, GetThread, ThreadRead

router = APIRouter(tags=["conversations"])


@router.get("/threads/{thread_id}")
def get_thread(thread_id: Annotated[str, Path(max_length=THREAD_ID_MAX_LENGTH)], bus: BusDep) -> ThreadRead:
    return bus.ask(GetThread(thread_id=thread_id))
