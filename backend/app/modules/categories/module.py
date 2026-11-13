"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it."""

from app.core.cqrs import MessageBus
from app.modules.categories import commands, queries
from app.modules.categories.api import router
from app.modules.categories.contracts import CreateCategory, FindCategoryByName, GetCategory, ListCategories
from app.modules.categories.tables import TABLES


def register_handlers(bus: MessageBus) -> None:
    bus.register(CreateCategory, commands.create_category)
    bus.register(ListCategories, queries.list_categories)
    bus.register(GetCategory, queries.get_category)
    bus.register(FindCategoryByName, queries.find_category_by_name)


__all__ = ["TABLES", "register_handlers", "router"]
