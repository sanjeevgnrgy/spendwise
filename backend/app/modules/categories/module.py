"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The categories module's wiring. bootstrap.py calls register_handlers() when it builds the bus, mounts
`router`, and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
Each message and its handler come from the same slice file, in commands/ or queries/.
"""

from app.core.cqrs import MessageBus
from app.modules.categories.api import router
from app.modules.categories.commands.create_category import CreateCategory, create_category
from app.modules.categories.persistence.tables import TABLES
from app.modules.categories.queries.find_category_by_name import FindCategoryByName, find_category_by_name
from app.modules.categories.queries.get_category import GetCategory, get_category
from app.modules.categories.queries.list_categories import ListCategories, list_categories


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries.

    One handler per message: registering a message twice raises ValueError (a wiring mistake).
    """
    bus.register(CreateCategory, create_category)
    bus.register(ListCategories, list_categories)
    bus.register(GetCategory, get_category)
    bus.register(FindCategoryByName, find_category_by_name)


__all__ = ["TABLES", "register_handlers", "router"]
