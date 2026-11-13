"""Run the SpendWise MCP server over stdio, for local tools (MCP Inspector, Claude Desktop).

The tool starts this script itself and talks to it through stdin/stdout, so no web server
is needed. From the project folder:  .\\.venv\\Scripts\\python.exe backend\\mcp_stdio.py

Never print() here: stdout carries the protocol messages, and stray text would corrupt them.
(Logging is fine; it goes to stderr.)
"""

from app.core.db import create_db_and_tables
from app.core.logging import setup_logging

# `mcp dev` and `mcp run` look for a global named "server" in this file.
from app.modules.mcp.server import server

setup_logging()
# This may run before the web app ever has, so make sure the tables exist.
create_db_and_tables()

if __name__ == "__main__":
    server.run()  # stdio is the default transport
