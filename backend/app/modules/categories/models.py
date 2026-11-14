"""The categories module's read model: CategoryRead, the frozen copy of a category that every query returns.

Part of the module's contract layer. The query slices (queries/) build it from table rows, api.py sends it from
GET /categories, and __init__.py exports it to other modules.
"""

from pydantic import BaseModel, ConfigDict


# What every category query returns, and what GET /categories sends. A Pydantic model, so its docstring
# below is part of the API schema: explanations go in these comments instead.
class CategoryRead(BaseModel):
    """A category as other code sees it: a frozen copy, never the table row."""

    # from_attributes builds it straight from a row; frozen means nobody can change our data through it.
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    name: str
    icon: str
