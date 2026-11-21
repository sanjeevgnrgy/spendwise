"""Runs the currency agent: `python -m currency`, with backend/ and agents/ on PYTHONPATH (run-agent.ps1 currency).

The entry point. Reads the settings (it stops here, naming the setting, if CURRENCY_AGENT_KEY is missing or short),
then serves the app on 127.0.0.1 at CURRENCY_AGENT_PORT, the address its Agent Card gives.
"""

from agent_kit.server import serve
from currency.server import create_app
from currency.settings import AgentSettings


def main() -> None:
    """Serve the agent until stopped (Ctrl+C)."""
    settings = AgentSettings()  # pyright: ignore[reportCallIssue]  (the key comes from the environment)
    serve(create_app(settings), settings.currency_agent_port)


if __name__ == "__main__":
    main()
