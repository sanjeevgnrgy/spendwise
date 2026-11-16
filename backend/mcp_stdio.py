"""Run the SpendWise MCP server over stdio, for local tools (MCP Inspector, Claude Desktop).

An entry point, built from the composition root: the same MCP server (and bus) the web app serves at /mcp/.

The tool starts this script itself and talks to it through stdin/stdout, so no web server
is needed. From the project folder:  .\\.venv\\Scripts\\python.exe backend\\mcp_stdio.py

It acts for one person: the owner of the personal access token in the SPENDWISE_TOKEN environment variable (made in
SpendWise's Settings; the tool's configuration sets it). Every tool call checks the token again, so revoking it, or
its expiry, stops the tools at once; without a working token every call is refused (D191).

Never print() here: stdout carries the protocol messages, and stray text would corrupt them.
(Logging is fine; it goes to stderr.)
"""

import logging
import os

from app import bootstrap
from app.infrastructure import migrations
from app.infrastructure.logging import setup_logging
from app.modules.mcp import act_for_process

# The environment variable that holds the personal access token this server acts with.
TOKEN_VARIABLE = "SPENDWISE_TOKEN"

logger = logging.getLogger(__name__)

# `mcp dev` and `mcp run` import this file (without running __main__) and look for a global named
# "server", so the setup happens at import: the logging, the tables brought up to date, then the same
# server the web app uses, from the composition root, acting for the token's owner.
setup_logging()
migrations.upgrade_to_latest()
services = bootstrap.build()
server = services.mcp_server
_token = os.environ.get(TOKEN_VARIABLE, "")
act_for_process(lambda: services.access_tokens.resolve(_token))
if services.access_tokens.resolve(_token) is None:
    # Never the token itself in the log: only that it's missing or doesn't work.
    logger.warning("%s is missing or doesn't work: every tool call will be refused until it's fixed.", TOKEN_VARIABLE)

if __name__ == "__main__":
    server.run()  # stdio is the default transport
