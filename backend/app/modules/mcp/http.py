"""MCP over HTTP ("Streamable HTTP"), for MCP clients that connect by URL.

Two locks on the door:
- **DNS-rebinding protection** (the SDK's default for a server on 127.0.0.1): requests whose Host or
  Origin header isn't a local address are refused, so a web page can't reach the tools through the
  user's browser.
- **A bearer token** (below): every request must carry "Authorization: Bearer <MCP_TOKEN>". Without
  it, any program that can reach the port could change or delete expenses.
"""

import hmac

from mcp.server.mcpserver import MCPServer
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import UNAUTHORIZED_SLUG, problem_response

AUTHORIZATION = b"authorization"
BEARER = "bearer"
UNAUTHORIZED_DETAIL = "Send the MCP token as 'Authorization: Bearer <token>'."


class BearerTokenAuth:
    """ASGI middleware: answer 401 unless the request carries the expected bearer token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self._app = app
        self._token = token.encode()

    def _authorized(self, header: bytes) -> bool:
        # "Bearer" is case-insensitive (RFC 9110 §11.1): "bearer abc" is as valid as "Bearer abc".
        scheme, _, token = header.decode("latin-1").partition(" ")
        # compare_digest takes the same time however much of the token matches, so the token can't be
        # guessed one character at a time by timing the answers.
        return scheme.lower() == BEARER and hmac.compare_digest(token.strip().encode("latin-1"), self._token)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not self._authorized(dict(scope["headers"]).get(AUTHORIZATION, b"")):
            response = problem_response(
                401, UNAUTHORIZED_SLUG, "Unauthorized", UNAUTHORIZED_DETAIL, scope.get("path", ""),
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


def create_http_app(server: MCPServer, token: str) -> ASGIApp:
    # stateless + JSON responses: each MCP request is answered on its own, with no per-client
    # session kept in memory, which is all our simple request/response tools need.
    inner = server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)
    return BearerTokenAuth(inner, token)
