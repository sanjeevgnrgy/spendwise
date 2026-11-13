"""Command handlers: the only code that writes conversations. The bus commits; handlers never do."""

from app.core.cqrs import Context
from app.modules.conversations.contracts import AppendTurn
from app.modules.conversations.tables import ConversationMessage


def append_turn(ctx: Context, command: AppendTurn) -> None:
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
