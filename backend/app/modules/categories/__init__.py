"""Categories module: the list of spending categories (Food, Transport, ...).

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.categories`, and send them through the bus. Tables, handlers and the router stay private to
this module; the composition root (bootstrap.py) plugs those in through module.py.

Inside, each command and each query is one file holding the message and its handler (commands/, queries/).
What several of them share is in values.py (limits, field types) and models.py (CategoryRead), its texts for
people in every language in i18n/ (CategoryText), and the table is in persistence/. This file only re-exports the
contract names from those files.

Who uses it: expenses (GetCategory checks that an expense's category exists, since there is no foreign
key; ListCategories names the categories in a summary), the MCP server (FindCategoryByName turns the
category name a model sends into an id; GetCategory names one expense's category, ListCategories a whole
list's), the assistant (category names for /parse, MAX_NAME_LENGTH for chart labels) and seed.py
(CreateCategory).
"""

from app.modules.categories.commands.create_category import CreateCategory
from app.modules.categories.i18n import CategoryText
from app.modules.categories.models import CategoryRead
from app.modules.categories.queries.find_category_by_name import FindCategoryByName
from app.modules.categories.queries.get_category import GetCategory
from app.modules.categories.queries.list_categories import ListCategories
from app.modules.categories.values import MAX_NAME_LENGTH, UNKNOWN_CATEGORY, CategoryId

__all__ = [
    "MAX_NAME_LENGTH",
    "UNKNOWN_CATEGORY",
    "CategoryId",
    "CategoryRead",
    "CategoryText",
    "CreateCategory",
    "FindCategoryByName",
    "GetCategory",
    "ListCategories",
]
