"""The categories module's texts for people, in English: their keys, and the source every other language translates.

Part of the categories module (i18n/): the errors it raises, and the "no categories yet" message other modules raise
(the assistant's /parse, the MCP tools). hi.py translates them; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class CategoryText(StrEnum):
    """The categories module's texts, by key."""

    ALREADY_EXISTS = "errors.alreadyExists"
    NO_CATEGORIES_YET = "errors.noCategoriesYet"


EN: dict[CategoryText, TextValue] = {
    CategoryText.ALREADY_EXISTS: "Category '{name}' already exists",
    # Said by anything that needs a category before any exist.
    CategoryText.NO_CATEGORIES_YET: "There are no categories yet. Add some (or run backend/seed.py) first.",
}
