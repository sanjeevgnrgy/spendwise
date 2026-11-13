"""Console logging for SpendWise's own messages, such as the assistant's steps and tool calls."""

import logging


def setup_logging() -> None:
    # Show our own INFO messages (loggers named "spendwise..."), while libraries stay quiet
    # unless something goes wrong. Uvicorn keeps its own log setup for request lines.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        # Creating the MCP server (imported before this runs) already sets up root logging at INFO, and
        # basicConfig does nothing once handlers exist. force=True replaces that setup with ours.
        force=True,
    )
    logging.getLogger("spendwise").setLevel(logging.INFO)
