"""MCP over HTTP ("Streamable HTTP"), for MCP clients that connect by URL.

Two locks on the door:
- **DNS-rebinding protection** (the SDK's default for a server on 127.0.0.1): requests whose Host or
  Origin header isn't a local address are refused, so a web page can't reach the tools through the
  user's browser.
- **A bearer token** (below): every request must carry "Authorization: Bearer <MCP_TOKEN>". Without
  it, any program that can reach the port could change or delete expenses.

Part of the mcp adapter, reached through module.py: main.py mounts create_http_app's result at /mcp/, and
only when MCP_TOKEN is set. A wrong or missing token gets a 401 problem-details response (core/errors.py).
"""

import hmac

from mcp.server.mcpserver import MCPServer
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import UNAUTHORIZED_SLUG, problem_response
from app.modules.mcp.contracts import AUTHORIZATION_HEADER, BEARER_SCHEME

# ASGI gives header names in lower case, as bytes.
AUTHORIZATION = AUTHORIZATION_HEADER.lower().encode()
BEARER = BEARER_SCHEME.lower()  # compared case-insensitively, see _authorized
UNAUTHORIZED_TITLE = "Unauthorized"
WWW_AUTHENTICATE = "WWW-Authenticate"  # tells a client which scheme to use (RFC 9110 §11.6.1)
UNAUTHORIZED_DETAIL = f"Send the MCP token as '{AUTHORIZATION_HEADER}: {BEARER_SCHEME} <token>'."


class BearerTokenAuth:
    """ASGI middleware: answer 401 unless the request carries the expected bearer token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        """Wrap `app` (the MCP endpoint), letting through only requests that carry `token`."""
        self._app = app
        self._token = token.encode()

    def _authorized(self, header: bytes) -> bool:
        """Whether an Authorization header's value is "Bearer <the expected token>"."""
        # "Bearer" is case-insensitive (RFC 9110 §11.1): "bearer abc" is as valid as "Bearer abc".
        scheme, _, token = header.decode("latin-1").partition(" ")
        # compare_digest takes the same time however much of the token matches, so the token can't be
        # guessed one character at a time by timing the answers.
        return scheme.lower() == BEARER and hmac.compare_digest(token.strip().encode("latin-1"), self._token)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer an HTTP request without the right token with 401; pass everything else to the app.

        Only "http" requests are checked: lifespan events carry no headers and must still reach the app.
        """
        if scope["type"] == "http" and not self._authorized(dict(scope["headers"]).get(AUTHORIZATION, b"")):
            response = problem_response(
                401, UNAUTHORIZED_SLUG, UNAUTHORIZED_TITLE, UNAUTHORIZED_DETAIL, scope.get("path", ""),
                headers={WWW_AUTHENTICATE: BEARER_SCHEME},
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


def create_http_app(server: MCPServer, token: str) -> ASGIApp:
    """The server's Streamable HTTP endpoint behind the bearer-token check, ready to mount at /mcp/."""
    # stateless + JSON responses: each MCP request is answered on its own, with no per-client
    # session kept in memory, which is all our simple request/response tools need.
    inner = server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)
    return BearerTokenAuth(inner, token)
