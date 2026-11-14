"""Command handlers: the only code that writes conversations. The bus commits; handlers never do.

Part of the conversations module's write side. module.py registers each handler with the bus; the
assistant sends the command (bus.execute(AppendTurn(...))) and never calls a handler directly.
"""

from app.core.cqrs import Context
from app.modules.conversations.contracts import AppendTurn
from app.modules.conversations.tables import ConversationMessage


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
