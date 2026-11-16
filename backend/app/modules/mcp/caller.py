"""Who an MCP request acts for: its caller, a person's user id, set by whatever received the request (D191).

Part of the mcp adapter. The tools and the "recent" resource read the caller here (current_caller), and only
ever touch that person's expenses. Three places set it, each from something the request itself can't forge:
- the HTTP endpoint (http.py), from the personal access token in the Authorization header;
- the stdio server (backend/mcp_stdio.py), from the token in its environment, for the whole process;
- the assistant (assistant/tools/mcp_adapter.py), for the person signed in to the web app, around each call.

Nothing in an MCP message (arguments, `_meta`) can name a caller. It's a context variable: asyncio tasks and
anyio's worker threads copy the context they start in, so the value set around a request reaches the tool
function that serves it, and two requests at once each see their own.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from app.core.errors import AuthenticationError

# Answers the caller's user id, asked on every tool call: None once the credentials stop working (the stdio
# server's token revoked or expired since it started).
CallerLookup = Callable[[], int | None]

# What an MCP client is told when no caller is set or its credentials stopped working (English: only MCP clients
# and the model read it).
NOT_SIGNED_IN = "This MCP connection isn't signed in, or its access token no longer works: use a valid token."

_caller: ContextVar[CallerLookup | None] = ContextVar("spendwise_mcp_caller", default=None)


def _lookup_for(who: int | CallerLookup) -> CallerLookup:
    """A lookup for a fixed user id, or the lookup itself."""
    if isinstance(who, int):
        return lambda: who
    return who


@contextmanager
def acting_for(who: int | CallerLookup) -> Iterator[None]:
    """Serve the MCP requests started inside the block for `who`: a user id, or a lookup asked on each call.

    The previous caller (usually none) is back when the block ends, even if it raises.
    """
    token = _caller.set(_lookup_for(who))
    try:
        yield
    finally:
        _caller.reset(token)


def act_for_process(lookup: CallerLookup) -> None:
    """Serve every MCP request of this process for whoever `lookup` names: for a server that runs for one person
    (stdio), set before it starts. `mcp run` imports the server and starts it later, so this can't be a block."""
    _caller.set(lookup)


def current_caller() -> int:
    """The user id the current MCP request acts for.

    Raises AuthenticationError (an MCP tool error) if no caller is set, or its credentials no longer work: a tool
    never falls back to anyone's data.
    """
    lookup = _caller.get()
    user_id = lookup() if lookup is not None else None
    if user_id is None:
        raise AuthenticationError(NOT_SIGNED_IN)
    return user_id
