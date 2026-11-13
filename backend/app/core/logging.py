"""Console logging for SpendWise's own messages, such as the assistant's steps and tool calls."""

import logging

# Every module logs with logging.getLogger(__name__), so all our loggers live under "app".
APP_LOGGER = "app"


def setup_logging(level: int = logging.INFO) -> None:
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
    logging.getLogger(APP_LOGGER).setLevel(level)
