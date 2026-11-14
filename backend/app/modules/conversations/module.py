"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The conversations module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
"""

from app.core.cqrs import MessageBus
from app.modules.conversations import commands, queries
from app.modules.conversations.api import router
from app.modules.conversations.contracts import AppendTurn, GetHistory, GetLastTurn, GetThread
from app.modules.conversations.tables import TABLES


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(AppendTurn, commands.append_turn)
    bus.register(GetLastTurn, queries.last_turn)
    bus.register(GetHistory, queries.history)
    bus.register(GetThread, queries.thread)


__all__ = ["TABLES", "register_handlers", "router"]
