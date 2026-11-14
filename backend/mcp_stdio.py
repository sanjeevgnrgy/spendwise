"""Run the SpendWise MCP server over stdio, for local tools (MCP Inspector, Claude Desktop).

An entry point, built from the composition root: the same MCP server (and bus) the web app serves at /mcp/.

The tool starts this script itself and talks to it through stdin/stdout, so no web server
is needed. From the project folder:  .\\.venv\\Scripts\\python.exe backend\\mcp_stdio.py

Never print() here: stdout carries the protocol messages, and stray text would corrupt them.
(Logging is fine; it goes to stderr.)
"""

from app import bootstrap, migrations
from app.core.logging import setup_logging

# `mcp dev` and `mcp run` import this file (without running __main__) and look for a global named
# "server", so the setup happens at import: the logging, the tables brought up to date, then the same
# server the web app uses, from the composition root.
setup_logging()
migrations.upgrade_to_latest()
server = bootstrap.build().mcp_server

if __name__ == "__main__":
    server.run()  # stdio is the default transport
