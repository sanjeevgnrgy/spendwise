"""Console logging for SpendWise's own messages, such as the assistant's steps and tool calls."""

import logging


def setup_logging() -> None:
    # Show our own INFO messages (loggers named "spendwise..."), while libraries stay quiet
    # unless something goes wrong. Uvicorn keeps its own log setup for request lines.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("spendwise").setLevel(logging.INFO)
