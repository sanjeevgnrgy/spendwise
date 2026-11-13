"""FastAPI dependencies for the shared services the composition root (main.py) creates.

Routes declare `bus: BusDep` or `clock: ClockDep` instead of importing a global, so anything that
builds the app (a script, a check) can hand in its own bus or a fixed clock.
"""

from typing import Annotated

from fastapi import Depends, Path, Request

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.db import MAX_ID


def get_bus(request: Request) -> MessageBus:
    return request.app.state.bus


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


BusDep = Annotated[MessageBus, Depends(get_bus)]
ClockDep = Annotated[Clock, Depends(get_clock)]
# An id in a URL path: one the database could hold. Anything bigger is a 422, not a driver crash.
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]
