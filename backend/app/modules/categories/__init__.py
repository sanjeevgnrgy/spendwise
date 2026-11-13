"""Categories module: the list of spending categories (Food, Transport, ...).

Public interface: other modules import ONLY the contract names below, from `app.modules.categories`,
and send them through the bus. Tables, handlers and the router stay private to this module.
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
