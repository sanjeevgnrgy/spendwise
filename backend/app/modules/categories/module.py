"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The categories module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
"""

from app.core.cqrs import MessageBus
from app.modules.categories import commands, queries
from app.modules.categories.api import router
from app.modules.categories.contracts import CreateCategory, FindCategoryByName, GetCategory, ListCategories
from app.modules.categories.tables import TABLES


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(CreateCategory, commands.create_category)
    bus.register(ListCategories, queries.list_categories)
    bus.register(GetCategory, queries.get_category)
    bus.register(FindCategoryByName, queries.find_category_by_name)


__all__ = ["TABLES", "register_handlers", "router"]
