"""The categories module's contract: the commands, queries and data other code may use.

Everything another module (or the composition root) needs from categories is defined here and
exported from the package's __init__.py. Tables, handlers and the router stay private.

What's here: the limits and fixed texts other modules share, the CategoryRead copy that every query
returns, one command (CreateCategory) and three queries (ListCategories, GetCategory, FindCategoryByName).
The handlers for them are in commands.py and queries.py.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.cqrs import Command, Query
from app.core.ids import RecordId

# The same limits as the table's columns (tables.py), so a name that passes here always fits there.
MAX_NAME_LENGTH = 50
MAX_ICON_LENGTH = 50

# What a list shows for an expense whose category no longer exists (expenses keep only the id, with
# no foreign key, so a category could disappear).
UNKNOWN_CATEGORY = "Unknown"
# Said by anything that needs a category before any exist (the assistant, the MCP tools).
NO_CATEGORIES_YET = "There are no categories yet. Add some (or run backend/seed.py) first."

CategoryId = RecordId
# Spaces around a name are removed: " Food" and "Food" would look identical in every list. The type only
# limits the length; the trimming comes from str_strip_whitespace on the messages that use it, and runs
# before the length check, so a name of only spaces is refused.
CategoryName = Annotated[str, Field(min_length=1, max_length=MAX_NAME_LENGTH)]
# An icon name (e.g. "utensils") that the frontend maps to a picture: plain text everywhere.
IconName = Annotated[str, Field(min_length=1, max_length=MAX_ICON_LENGTH)]


# What every category query returns, and what GET /categories sends. A Pydantic model, so its docstring
# below is part of the API schema: explanations go in these comments instead.
class CategoryRead(BaseModel):
    """A category as other code sees it: a frozen copy, never the table row."""

    # from_attributes builds it straight from a row; frozen means nobody can change our data through it.
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    name: str
    icon: str


# ---------- commands ----------


# Add a category (seed.py does; there's no REST route for it yet). The handler refuses a name that
# already exists in any letter case, with a BusinessRuleError (commands.create_category).
class CreateCategory(Command[int]):
    """Returns the new category's id."""

    # Trim stray spaces from both fields before they're checked and stored.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName
    icon: IconName


# ---------- queries ----------


# Answers GET /categories, names the categories in summaries and MCP results, and gives the assistant
# and seed.py the list.
class ListCategories(Query[list[CategoryRead]]):
    """Every category, in the order they were created."""


# The expenses module's "does this category exist?" check before it saves an expense (there is no
# foreign key to do it). The MCP tools also use it to name one expense's category.
class GetCategory(Query[CategoryRead | None]):
    """One category, or None if it doesn't exist (callers use it as a "does it exist?" check)."""

    category_id: CategoryId


# How a name typed by a person or a model becomes a category (the MCP tools), and how CreateCategory
# spots a duplicate. Spaces around the name are trimmed first; the letter case is compared in the
# database (queries.find_category_by_name).
class FindCategoryByName(Query[CategoryRead | None]):
    """The category with this name in any letter case ("food" finds "Food"), or None."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName
