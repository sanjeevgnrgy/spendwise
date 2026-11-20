"""Console logging for SpendWise's own messages, such as the assistant's steps and tool calls (infrastructure).

Called once by each entry point before it starts working: main.create_app (the web app), mcp_stdio.py and the
receipt agent (agents/receipt/server.py, which adds its own "receipt" loggers).
"""

import logging
from collections.abc import Iterable

# Every module logs with logging.getLogger(__name__), so all our loggers live under "app".
APP_LOGGER = "app"


def setup_logging(level: int = logging.INFO, loggers: Iterable[str] = ()) -> None:
    """Show our own loggers ("app.*", and any in `loggers`) at `level` on the console; other libraries only from
    WARNING up."""
    # Show our own messages, while libraries stay quiet unless something goes wrong. Uvicorn keeps
    # its own log setup for request lines.
    # Message text, tool arguments and form values are logged only at DEBUG: they're the user's
    # financial data, and INFO logs are the ones that get kept and shipped around.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        # Creating the MCP server (imported before this runs) already sets up root logging at INFO, and
        # basicConfig does nothing once handlers exist. force=True replaces that setup with ours.
        force=True,
    )
    for name in (APP_LOGGER, *loggers):
        logging.getLogger(name).setLevel(level)
