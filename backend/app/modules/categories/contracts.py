"""The categories module's contract: the commands, queries and data other code may use.

Everything another module (or the composition root) needs from categories is defined here and
exported from the package's __init__.py. Tables, handlers and the router stay private.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.cqrs import Command, Query
from app.core.db import RecordId

MAX_NAME_LENGTH = 50
MAX_ICON_LENGTH = 50

# What a list shows for an expense whose category no longer exists (expenses keep only the id, with
# no foreign key, so a category could disappear).
UNKNOWN_CATEGORY = "Unknown"
# Said by anything that needs a category before any exist (the assistant, the MCP tools).
NO_CATEGORIES_YET = "There are no categories yet. Add some (or run backend/seed.py) first."

CategoryId = RecordId
# Spaces around a name are removed: " Food" and "Food" would look identical in every list.
CategoryName = Annotated[str, Field(min_length=1, max_length=MAX_NAME_LENGTH)]
# An icon name (e.g. "utensils") that the frontend maps to a picture: plain text everywhere.
IconName = Annotated[str, Field(min_length=1, max_length=MAX_ICON_LENGTH)]


class CategoryRead(BaseModel):
    """A category as other code sees it: a frozen copy, never the table row."""

    # from_attributes builds it straight from a row; frozen means nobody can change our data through it.
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    name: str
    icon: str


# ---------- commands ----------


class CreateCategory(Command[int]):
    """Returns the new category's id."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName
    icon: IconName


# ---------- queries ----------


class ListCategories(Query[list[CategoryRead]]):
    """Every category, in the order they were created."""


class GetCategory(Query[CategoryRead | None]):
    """One category, or None if it doesn't exist (callers use it as a "does it exist?" check)."""

    category_id: CategoryId


class FindCategoryByName(Query[CategoryRead | None]):
    """The category with this name in any letter case ("food" finds "Food"), or None."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName
