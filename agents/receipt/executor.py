"""The receipt agent's AgentExecutor: one request becomes one task, read once, answered with a data artifact.

Application layer of the receipt agent. The SDK's request handler (server.py) calls execute() for each SendMessage;
it reads the message's two parts, moves the task through its states and publishes them on the event queue:

    SUBMITTED -> WORKING -> COMPLETED, with the ReceiptExtraction artifact
                         -> FAILED     the model couldn't read it (LlmError)
              -> REJECTED                the request isn't what the skill takes (wrong parts, type, size or data)

A rejection or failure carries a short English reason for the client's log; the client shows people its own texts.
"""

import asyncio
import logging

from pydantic import ValidationError

from a2a.helpers import get_data_parts, new_data_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part
from a2a.utils.errors import TaskNotCancelableError

from agent_kit.tasks import fail, reject, start_task
from app.core.llm import LlmError
from receipt.contract import (
    ARTIFACT_NAME,
    JSON_MEDIA_TYPE,
    MAX_RECEIPT_BYTES,
    ReadingRequest,
    ReceiptMediaType,
)
from receipt.reader import ReceiptReader

logger = logging.getLogger(__name__)

# The reasons a task ends without an answer (English, for the client's log; never shown to a person).
WRONG_PARTS = "expected exactly one file part (raw bytes) and one data part"
WRONG_TYPE = "the file must be one of: " + ", ".join(ReceiptMediaType)
WRONG_SIZE = f"the file must be 1 to {MAX_RECEIPT_BYTES} bytes"
WRONG_DATA = "the data part isn't a ReadingRequest"
NOT_READ = "the receipt couldn't be read"


class RejectedRequest(Exception):
    """A request the skill doesn't take; its message is the reason sent back (one of the texts above)."""


class ReceiptExecutor(AgentExecutor):
    """Runs the extract_receipt skill for each request, with the ReceiptReader it's given."""

    def __init__(self, reader: ReceiptReader) -> None:
        """Keep the reader; it does the one model call per task."""
        self._reader = reader

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Read the request's receipt and publish the task's states and its artifact. Raises nothing for a bad
        request or a failed reading: they end the task as REJECTED or FAILED, with a reason."""
        message, updater = await start_task(context, event_queue)
        try:
            file, request = _inputs(message)
        except RejectedRequest as exc:
            logger.info("task %s rejected: %s", updater.task_id, exc)
            await reject(updater, str(exc))
            return
        await updater.start_work()
        try:
            # The model port is synchronous: read in a worker thread, so the server keeps answering meanwhile.
            extraction = await asyncio.to_thread(self._reader.read, file.raw, file.media_type, request)
        except LlmError as exc:
            # The model's own words go to the log only; the client gets a fixed reason.
            logger.warning("task %s failed: %s", updater.task_id, exc)
            await fail(updater, NOT_READ)
            return
        answer = new_data_part(extraction.model_dump(mode="json"), media_type=JSON_MEDIA_TYPE)
        await updater.add_artifact(parts=[answer], name=ARTIFACT_NAME, last_chunk=True)
        await updater.complete()
        logger.info("task %s completed", updater.task_id)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported: a reading is one model call that can't be stopped half-way. Raises TaskNotCancelableError."""
        raise TaskNotCancelableError()


def _inputs(message: Message) -> tuple[Part, ReadingRequest]:
    """The request's file part and its ReadingRequest, checked. Raises RejectedRequest with the reason."""
    files = [part for part in message.parts if part.HasField("raw")]
    data = get_data_parts(message.parts)
    if len(files) != 1 or len(data) != 1 or len(message.parts) != len(files) + len(data):
        raise RejectedRequest(WRONG_PARTS)
    file = files[0]
    # The client judged the type by the file's bytes (the monolith's upload check); the agent still accepts only
    # the types it states, so the model is never told one it can't read.
    if file.media_type not in set(ReceiptMediaType):
        raise RejectedRequest(WRONG_TYPE)
    if not 0 < len(file.raw) <= MAX_RECEIPT_BYTES:
        raise RejectedRequest(WRONG_SIZE)
    try:
        request = ReadingRequest.model_validate(data[0])
    except ValidationError as exc:
        raise RejectedRequest(WRONG_DATA) from exc
    return file, request
