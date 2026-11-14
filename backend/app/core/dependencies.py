"""FastAPI dependencies for the shared services the composition root creates (core infrastructure).

bootstrap.build() creates one bus and one clock, and main.create_app stores them on `app.state`.
Routes (every module's api.py) declare `bus: BusDep` or `clock: ClockDep` instead of importing a global, so
anything that builds the app (a script, a check) can hand in its own bus or a fixed clock.
"""

from typing import Annotated

from fastapi import Depends, Path, Request

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.ids import MAX_ID


def get_bus(request: Request) -> MessageBus:
    """The app's one MessageBus, as main.create_app stored it."""
    return request.app.state.bus


def get_clock(request: Request) -> Clock:
    """The app's Clock, as main.create_app stored it."""
    return request.app.state.clock


# Annotated types, so a route parameter only needs `bus: BusDep`: FastAPI then calls get_bus for it.
BusDep = Annotated[MessageBus, Depends(get_bus)]
ClockDep = Annotated[Clock, Depends(get_clock)]
# An id in a URL path: one the database could hold. Anything bigger is a 422, not a driver crash.
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]
