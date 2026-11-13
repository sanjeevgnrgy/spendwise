"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it."""

from app.core.cqrs import MessageBus
from app.modules.conversations import commands, queries
from app.modules.conversations.api import router
from app.modules.conversations.contracts import AppendTurn, GetHistory, GetLastTurn, GetThread
from app.modules.conversations.tables import TABLES


def register_handlers(bus: MessageBus) -> None:
    bus.register(AppendTurn, commands.append_turn)
    bus.register(GetLastTurn, queries.last_turn)
    bus.register(GetHistory, queries.history)
    bus.register(GetThread, queries.thread)


__all__ = ["TABLES", "register_handlers", "router"]
