"""FastAPI dependencies for the shared services the composition root creates, and the request's language (web layer).

bootstrap.build() creates one bus and one clock, and main.create_app stores them on `app.state`.
Routes (every module's api.py) declare `bus: BusDep` or `clock: ClockDep` instead of importing a global, so
anything that builds the app (a script, a check) can hand in its own bus or a fixed clock. A route that writes texts
for people (the assistant's) declares `language: LanguageDep`; web/problems.py reads the same for error details.
"""

from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, Path, Request

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.i18n import Language, parse_accept_language
from app.core.ids import MAX_ID

# The request header a client names its languages in (RFC 9110 §12.5.4). The web app sends the one it shows.
ACCEPT_LANGUAGE = "Accept-Language"


def get_bus(request: Request) -> MessageBus:
    """The app's one MessageBus, as main.create_app stored it."""
    return request.app.state.bus


def get_clock(request: Request) -> Clock:
    """The app's Clock, as main.create_app stored it."""
    return request.app.state.clock


def language_of(headers: Mapping[str, str]) -> Language:
    """The language a request's headers ask for: the best match for Accept-Language, else English. Shared by
    get_language and web/problems.py's middleware (which has headers, not a Request)."""
    return parse_accept_language(headers.get(ACCEPT_LANGUAGE))


def get_language(request: Request) -> Language:
    """The language to answer this request in: the best match for its Accept-Language, else English."""
    # Read from the request rather than declared as a Header parameter: content negotiation isn't part of any one
    # route's API, so it stays out of the OpenAPI document.
    return language_of(request.headers)


# Annotated types, so a route parameter only needs `bus: BusDep`: FastAPI then calls get_bus for it.
BusDep = Annotated[MessageBus, Depends(get_bus)]
ClockDep = Annotated[Clock, Depends(get_clock)]
LanguageDep = Annotated[Language, Depends(get_language)]
# An id in a URL path: one the database could hold. Anything bigger is a 422, not a driver crash.
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]
