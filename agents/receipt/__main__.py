"""Runs the receipt agent: `python -m receipt`, with backend/ and agents/ on PYTHONPATH (run-receipt-agent.ps1).

The entry point. Reads the settings (it stops here, naming the setting, if RECEIPT_AGENT_KEY is missing or short),
then serves the app on 127.0.0.1 at RECEIPT_AGENT_PORT, the address its Agent Card gives.
"""

import uvicorn

from receipt.server import create_app
from receipt.settings import HOST, AgentSettings


def main() -> None:
    """Serve the agent until stopped (Ctrl+C)."""
    settings = AgentSettings()
    uvicorn.run(create_app(settings), host=HOST, port=settings.receipt_agent_port)


if __name__ == "__main__":
    main()
