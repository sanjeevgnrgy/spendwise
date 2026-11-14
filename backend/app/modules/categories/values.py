"""The categories module's shared values: its limits, fixed texts, id type and field types.

Part of the module's contract layer. The command and query slices (commands/, queries/) build their messages
from these types, and the table (persistence/tables.py) sizes its columns with the limits. __init__.py exports
the ones other modules use (MAX_NAME_LENGTH, UNKNOWN_CATEGORY, NO_CATEGORIES_YET, CategoryId). This file imports
no other file of the module, so every file in it can use it.
"""

from typing import Annotated

from pydantic import Field

from app.core.ids import RecordId

# The same limits as the table's columns (persistence/tables.py), so a name that passes here always fits there.
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
