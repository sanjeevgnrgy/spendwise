"""Categories module: the list of spending categories (Food, Transport, ...).

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.categories`, and send them through the bus. Tables, handlers and the router stay private to
this module; the composition root (bootstrap.py) plugs those in through module.py.

Who uses it: expenses (GetCategory checks that an expense's category exists, since there is no foreign
key; ListCategories names the categories in a summary), the MCP server (FindCategoryByName turns the
category name a model sends into an id; GetCategory names one expense's category, ListCategories a whole
list's), the assistant (category names for /parse, MAX_NAME_LENGTH for chart labels) and seed.py
(CreateCategory).
"""

from app.modules.categories.contracts import (
    MAX_NAME_LENGTH,
    NO_CATEGORIES_YET,
    UNKNOWN_CATEGORY,
    CategoryId,
    CategoryRead,
    CreateCategory,
    FindCategoryByName,
    GetCategory,
    ListCategories,
)

__all__ = [
    "MAX_NAME_LENGTH",
    "NO_CATEGORIES_YET",
    "UNKNOWN_CATEGORY",
    "CategoryId",
    "CategoryRead",
    "CreateCategory",
    "FindCategoryByName",
    "GetCategory",
    "ListCategories",
]
