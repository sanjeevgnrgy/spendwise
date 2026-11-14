"""How the composition root plugs this module in: the server itself, and its HTTP endpoint.

The mcp module's wiring. bootstrap.py calls create_server(bus) once; main.py wraps that server with
create_http_app(server, token) when MCP_TOKEN is set. Nothing else imports this file: other modules use
the contract in __init__.py, which loads no server code.
"""

from app.modules.mcp.http import create_http_app
from app.modules.mcp.server import create_server

__all__ = ["create_http_app", "create_server"]
