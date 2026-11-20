"""How the composition root plugs this module in: the server itself, and its HTTP endpoint.

The mcp module's wiring. bootstrap.py calls create_server(bus, recorder, monthly_reports, clock) once; main.py wraps
that server with create_http_app(server, resolve), where `resolve` (the accounts module's) turns a personal access token
into its owner. Nothing else imports this file: other modules use the contract in __init__.py, which loads no server
code.
"""

from app.modules.mcp.http import TokenResolver, create_http_app
from app.modules.mcp.server import create_server

__all__ = ["TokenResolver", "create_http_app", "create_server"]
