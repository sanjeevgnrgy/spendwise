"""The conversations module's shared values: the thread id's type, its length limit and the "not found" text.

Part of the module's contract layer. The command and query slices (commands/, queries/) use ThreadId in their
messages, and the table (persistence/tables.py) sizes its column with the limit. __init__.py exports all three;
the assistant uses them for its own thread ids. This file imports no other file of the module.
"""

from typing import Annotated

from pydantic import Field

# The longest thread id accepted: also the table column's length (persistence/tables.py).
THREAD_ID_MAX_LENGTH = 32
# The 404 text for a thread id with no messages; the assistant uses it too, for a /chat thread it can't continue.
THREAD_NOT_FOUND = "Thread {thread_id} not found"
# The browser names AG-UI threads; the server names /chat ones (a 32-character hex id).
ThreadId = Annotated[str, Field(min_length=1, max_length=THREAD_ID_MAX_LENGTH)]
