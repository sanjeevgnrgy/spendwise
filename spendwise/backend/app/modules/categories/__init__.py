"""Categories module: the list of spending categories (Food, Transport, ...).

Public interface: other modules import ONLY the names below, from `app.modules.categories`.
Models, repository and service internals stay private to this module.
"""

from app.modules.categories.schemas import CategoryCreate, CategoryRead
from app.modules.categories.service import create_category, get_category, list_categories

__all__ = ["CategoryCreate", "CategoryRead", "create_category", "get_category", "list_categories"]
