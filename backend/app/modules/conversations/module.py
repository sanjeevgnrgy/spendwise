"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The conversations module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
Each message and its handler come from the same slice file, in commands/ or queries/.
"""

from app.core.cqrs import MessageBus
from app.modules.conversations.api import router
from app.modules.conversations.commands.append_turn import AppendTurn, append_turn
from app.modules.conversations.persistence.tables import TABLES
from app.modules.conversations.queries.get_history import GetHistory, get_history
from app.modules.conversations.queries.get_last_turn import GetLastTurn, get_last_turn
from app.modules.conversations.queries.get_thread import GetThread, get_thread


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(AppendTurn, append_turn)
    bus.register(GetLastTurn, get_last_turn)
    bus.register(GetHistory, get_history)
    bus.register(GetThread, get_thread)


__all__ = ["TABLES", "register_handlers", "router"]
