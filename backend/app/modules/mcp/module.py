"""How the composition root plugs this module in: the server itself, and its HTTP endpoint."""

from app.modules.mcp.http import create_http_app
from app.modules.mcp.server import create_server

__all__ = ["create_http_app", "create_server"]
