"""MCP over HTTP ("Streamable HTTP"), for MCP clients that connect by URL.

Two locks on the door:
- **DNS-rebinding protection** (the SDK's default for a server on 127.0.0.1): requests whose Host or
  Origin header isn't a local address are refused, so a web page can't reach the tools through the
  user's browser.
- **A personal access token** (below): every request must carry "Authorization: Bearer <token>", a token someone
  created in SpendWise's Settings. The request then acts for that person, and only them (caller.py, D191).

Part of the mcp adapter, reached through module.py: main.py mounts create_http_app's result at /mcp/. A missing,
wrong, expired or revoked token gets a 401 problem-details response (web/problems.py).
"""

from collections.abc import Callable

import anyio.to_thread
from mcp.server.mcpserver import MCPServer
from starlette.types import ASGIApp, Receive, Scope, Send

from app.modules.mcp.caller import acting_for
from app.modules.mcp.contracts import AUTHORIZATION_HEADER, BEARER_SCHEME
from app.web.problems import UNAUTHORIZED_SLUG, problem_response

# Turns a token, as sent, into the user id of the person it belongs to; None if it doesn't work (unknown, expired,
# revoked, or its owner switched off). The accounts module's, handed in by the composition root.
TokenResolver = Callable[[str], int | None]

# ASGI gives header names in lower case, as bytes.
AUTHORIZATION = AUTHORIZATION_HEADER.lower().encode()
BEARER = BEARER_SCHEME.lower()  # compared case-insensitively, see _token_in
UNAUTHORIZED_TITLE = "Unauthorized"
WWW_AUTHENTICATE = "WWW-Authenticate"  # tells a client which scheme to use (RFC 9110 §11.6.1)
UNAUTHORIZED_DETAIL = (
    f"Send a personal access token as '{AUTHORIZATION_HEADER}: {BEARER_SCHEME} <token>' "
    "(create one in SpendWise's Settings)."
)


def _token_in(header: bytes) -> str | None:
    """The token of an Authorization header's "Bearer <token>" value, or None for any other value."""
    # "Bearer" is case-insensitive (RFC 9110 §11.1): "bearer abc" is as valid as "Bearer abc".
    scheme, _, token = header.decode("latin-1").partition(" ")
    token = token.strip()
    return token if scheme.lower() == BEARER and token else None


class AccessTokenAuth:
    """ASGI middleware: answer 401 unless the request carries a working personal access token, and serve it for the
    token's owner."""

    def __init__(self, app: ASGIApp, resolve: TokenResolver) -> None:
        """Wrap `app` (the MCP endpoint); `resolve` names the person a token belongs to."""
        self._app = app
        self._resolve = resolve

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve an HTTP request for its token's owner, or answer 401 without a working token.

        Only "http" requests are checked: lifespan events carry no headers and must still reach the app.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        token = _token_in(dict(scope["headers"]).get(AUTHORIZATION, b""))
        # The lookup reads the database: in a worker thread, so the event loop isn't held up. Only the token's hash
        # is compared (the accounts module stores nothing else), so its timing reveals nothing about the token.
        owner = await anyio.to_thread.run_sync(self._resolve, token) if token else None
        if owner is None:
            response = problem_response(
                401,
                UNAUTHORIZED_SLUG,
                UNAUTHORIZED_TITLE,
                UNAUTHORIZED_DETAIL,
                scope.get("path", ""),
                headers={WWW_AUTHENTICATE: BEARER_SCHEME},
            )
            await response(scope, receive, send)
            return
        # Everything the SDK starts for this request (its tasks, the tool's worker thread) copies this context, so
        # the tools see this owner, and only for this request.
        with acting_for(owner):
            await self._app(scope, receive, send)


def create_http_app(server: MCPServer, resolve: TokenResolver) -> ASGIApp:
    """The server's Streamable HTTP endpoint behind the access-token check, ready to mount at /mcp/."""
    # stateless + JSON responses: each MCP request is answered on its own, with no per-client
    # session kept in memory, which is all our simple request/response tools need.
    inner = server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)
    return AccessTokenAuth(inner, resolve)
