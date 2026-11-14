"""AppendTurn: store one finished turn of a thread. The command and its handler, the only code that writes threads.

A slice of the conversations module's write side. module.py registers the handler with the bus; the assistant
sends the command (bus.execute(AppendTurn(...))) once a run has succeeded, and never calls the handler directly.
The bus commits; the handler never does.
"""

from pydantic import Field

from app.core.cqrs import Command, Context
from app.core.llm import Message
from app.modules.conversations.persistence.tables import ConversationMessage
from app.modules.conversations.values import ThreadId


# Sent by the assistant once a run has finished. `turn` is the next number after GetLastTurn's (1 for a
# new thread); the messages are stored in the order given.
class AppendTurn(Command[None]):
    """Store one whole turn (it's saved only once the run has succeeded)."""

    thread_id: ThreadId
    turn: int = Field(ge=1)
    messages: list[Message]


def append_turn(ctx: Context, command: AppendTurn) -> None:
    """Stage every message of one turn as its own row, in order, stamped with the clock's now (UTC).

    Each message is stored as its provider-neutral JSON (core/llm/messages.py), so the history can be
    resent to whichever model is in use. The rows are only staged; the bus commits them together.
    """
    # One command, one transaction: a thread never holds half a turn.
    ctx.session.add_all(
        ConversationMessage(
            thread_id=command.thread_id,
            turn=command.turn,
            kind=message.kind,
            content=message.model_dump(mode="json"),
            created_at=ctx.clock.now(),
        )
        for message in command.messages
    )
