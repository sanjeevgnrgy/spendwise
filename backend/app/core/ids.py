"""The rules for record ids, shared by every module's contracts and routes (core layer).

Kept apart from infrastructure/db.py, so a module's contract can use them without importing the database layer (which
creates the default engine from DATABASE_URL as it's imported).
"""

from typing import Annotated

from pydantic import Field

# The largest integer SQLite can store. Ids above it can't exist, so inputs are capped here and get a
# clean 404/422, instead of crashing the database driver with an OverflowError (a 500).
MAX_ID = 2**63 - 1
# Any table's id, as callers may send it. (For a URL path, see web/dependencies.IdPath.)
RecordId = Annotated[int, Field(ge=1, le=MAX_ID)]
