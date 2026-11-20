"""Starting and ending a task, the same way in every agent's executor (agent kit).

start_task turns the request's message into the task (SUBMITTED, published at once so the client learns its id) and
returns its TaskUpdater; reject and fail end it with a short English reason for the client's log (D195). Used by the
receipt and currency agents' executors.
"""

from a2a.helpers import new_task_from_user_message, new_text_part
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message

# The SDK's handler always sets the message for SendMessage; an executor run without one is a wiring bug.
NO_MESSAGE = "no message in the request"


async def start_task(context: RequestContext, event_queue: EventQueue) -> tuple[Message, TaskUpdater]:
    """The request's message and an updater for its task, which is published (SUBMITTED) if it's new. Raises
    RuntimeError if there's no message."""
    message = context.message
    if message is None:
        raise RuntimeError(NO_MESSAGE)
    task = context.current_task or new_task_from_user_message(message)
    if context.current_task is None:
        await event_queue.enqueue_event(task)
    return message, TaskUpdater(event_queue, task.id, task.context_id)


async def reject(updater: TaskUpdater, reason: str) -> None:
    """End the task REJECTED (a request the skill doesn't take), with `reason`."""
    await updater.reject(updater.new_agent_message([new_text_part(reason)]))


async def fail(updater: TaskUpdater, reason: str) -> None:
    """End the task FAILED (the work couldn't be done), with `reason`."""
    await updater.failed(updater.new_agent_message([new_text_part(reason)]))
